from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.crud import contract as contract_crud
from app.schemas.contract import ContractCreate, ContractUpdate, ContractResponse, ContractListResponse

router = APIRouter()


@router.get("", response_model=ContractListResponse)
async def list_contracts(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    filters = {}
    if status:
        filters["status"] = status
    items, total = await contract_crud.contract.list(db, skip=skip, limit=limit, filters=filters)
    try:
        validated_items = [ContractResponse.model_validate(c) for c in items]
        return ContractListResponse(
            items=validated_items,
            total=total,
            page=(skip // limit) + 1,
            page_size=limit,
        )
    except Exception as e:
        print(f"Error validating contracts: {e}")
        import traceback
        traceback.print_exc()
        raise


@router.get("/{contract_id}", response_model=ContractResponse)
async def get_contract(
    contract_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    contract = await contract_crud.contract.get(db, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")
    return ContractResponse.model_validate(contract)


@router.post("", response_model=ContractResponse, status_code=201)
async def create_contract(
    contract_in: ContractCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    contract_no = await contract_crud.contract.generate_contract_no(db)

    obj_dict = contract_in.model_dump()
    db_obj = contract_crud.contract.model(**obj_dict, contract_no=contract_no)
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    contract = db_obj

    if contract.project_id:
        await contract_crud.contract.sync_amount_to_project(db, contract)

    return ContractResponse.model_validate(contract)


@router.put("/{contract_id}", response_model=ContractResponse)
async def update_contract(
    contract_id: int,
    contract_in: ContractUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contract = await contract_crud.contract.get(db, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")

    if contract_in.status == "terminated" and not contract_in.termination_reason:
        raise HTTPException(status_code=400, detail="合同终止必须填写原因")

    valid_transitions = {
        "draft": ["active"],
        "active": ["executing", "terminated"],
        "executing": ["completed", "terminated"],
    }
    if contract_in.status and contract.status != contract_in.status:
        allowed = valid_transitions.get(contract.status, [])
        if contract_in.status not in allowed:
            raise HTTPException(
                status_code=400, detail=f"合同状态不能从 '{contract.status}' 变更为 '{contract_in.status}'"
            )

    # Record amount change log before update
    old_amount = contract.amount
    should_log_amount = contract_in.amount is not None and old_amount != contract_in.amount

    contract = await contract_crud.contract.update(db, contract, contract_in)

    if should_log_amount:
        from app.crud import changelog as changelog_crud
        await changelog_crud.create_changelog(
            db, "contract", contract.id, "amount",
            str(old_amount), str(contract_in.amount),
            changed_by=current_user.id,
        )
        await db.commit()

    if contract_in.amount is not None:
        await contract_crud.contract.sync_amount_to_project(db, contract)

    return ContractResponse.model_validate(contract)


@router.delete("/{contract_id}")
async def delete_contract(
    contract_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    contract = await contract_crud.contract.get(db, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")

    if contract.status in ["active", "executing"]:
        raise HTTPException(status_code=400, detail="生效中的合同不可删除，请先终止")

    await contract_crud.contract.remove(db, contract_id)
    return {"message": "合同已删除"}


@router.get("/{contract_id}/invoices")
async def get_contract_invoices(
    contract_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取合同关联的发票列表。"""
    from app.crud.invoice import invoice as invoice_crud

    # 验证合同存在
    contract = await contract_crud.contract.get(db, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")

    items, total = await invoice_crud.list(
        db,
        skip=skip,
        limit=limit,
        contract_id=contract_id,
    )

    from app.schemas.invoice import InvoiceContractResponse
    return {
        "items": [InvoiceContractResponse.model_validate(i) for i in items],
        "total": total,
        "page": (skip // limit) + 1,
        "page_size": limit,
    }
