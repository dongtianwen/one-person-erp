from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import Optional

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.contract import Contract
from app.crud import contract as contract_crud
from app.crud.quotation import quotation as quotation_crud
from app.schemas.contract import ContractCreate, ContractUpdate, ContractResponse, ContractListResponse
from app.core.template_utils import build_contract_context, render_template
from app.crud.template import get_default_template
from app.core.error_codes import ERROR_CODES
from app.crud.project import project as project_crud

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


# ── 内容生成接口 ───────────────────────────────────────────

@router.post("/{contract_id}/generate", response_model=ContractResponse)
async def generate_contract_content(
    contract_id: int,
    force: bool = Query(False, description="是否强制覆盖已存在的内容"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """生成合同内容。

    - **force**: 是否强制覆盖（默认 false，内容已存在则返回 409）
    """
    content, _ = await contract_crud.contract.generate_contract_content(
        db=db, contract_id=contract_id, force=force
    )

    result = await db.execute(select(Contract).where(Contract.id == contract_id))
    contract = result.scalars().first()
    return ContractResponse.model_validate(contract)


@router.get("/{contract_id}/preview")
async def preview_contract_content(
    contract_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """预览合同内容（不写库）。

    允许在任何状态下预览，包括 active 冻结状态。
    """
    result = await db.execute(
        select(Contract)
        .options(selectinload(Contract.quotation))
        .where(Contract.id == contract_id)
    )
    contract = result.scalars().first()

    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")

    # 构建模板上下文
    contract_data = {
        "contract_no": contract.contract_no,
        "title": contract.title,
        "customer_name": "",
        "project_name": contract.title,
        "amount": contract.amount or 0,
        "signed_date": str(contract.signed_date) if contract.signed_date else "",
        "notes": contract.terms or "",
    }
    quotation_data = {}
    if contract.quotation:
        quotation_data = {"quote_no": contract.quotation.quote_no}

    context = build_contract_context(contract_data, quotation_data)

    # 获取默认模板
    template = await get_default_template(db, template_type="contract")
    if not template:
        raise HTTPException(status_code=404, detail="默认合同模板不存在")

    # 渲染模板（不写库）
    content, error_msg = render_template(
        template_content=template.content,
        context=context,
        required_vars=None,  # 预览不校验必填变量
    )

    if error_msg:
        raise HTTPException(status_code=500, detail=f"模板渲染失败: {error_msg}")

    return {"content": content}


@router.put("/{contract_id}/generated-content")
async def update_contract_content(
    contract_id: int,
    content: str = Query(..., description="新内容"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """手工编辑合同内容。

    content_generated_at 不更新（保留最后生成时间）。
    """
    try:
        await contract_crud.contract.update_contract_generated_content(
            db=db, contract_id=contract_id, content=content
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="合同不存在")

    return {"message": "内容已更新"}
