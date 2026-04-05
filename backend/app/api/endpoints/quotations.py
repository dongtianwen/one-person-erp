from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import date

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.crud.quotation import quotation as quotation_crud
from app.crud.contract import contract as contract_crud
from app.schemas.quotation import (
    QuotationCreate, QuotationUpdate, QuotationResponse, QuotationListResponse,
)

router = APIRouter()

EDITABLE_STATUSES = {"draft", "sent"}
VALID_STATUSES = {"draft", "sent", "accepted", "rejected", "expired"}


@router.get("", response_model=QuotationListResponse)
async def list_quotations(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    customer_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    filters = {}
    if status:
        filters["status"] = status
    if customer_id:
        filters["customer_id"] = customer_id
    items, total = await quotation_crud.list(db, skip=skip, limit=limit, filters=filters)
    return QuotationListResponse(
        items=[QuotationResponse.model_validate(q) for q in items],
        total=total,
        page=(skip // limit) + 1,
        page_size=limit,
    )


@router.get("/{quotation_id}", response_model=QuotationResponse)
async def get_quotation(
    quotation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = await quotation_crud.get(db, quotation_id)
    if not q:
        raise HTTPException(status_code=404, detail="报价单不存在")
    return QuotationResponse.model_validate(q)


@router.post("", response_model=QuotationResponse, status_code=201)
async def create_quotation(
    quotation_in: QuotationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    quotation_number = await quotation_crud.generate_quotation_number(db)
    obj_dict = quotation_in.model_dump()
    db_obj = quotation_crud.model(**obj_dict, quotation_number=quotation_number)
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return QuotationResponse.model_validate(db_obj)


@router.put("/{quotation_id}", response_model=QuotationResponse)
async def update_quotation(
    quotation_id: int,
    quotation_in: QuotationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = await quotation_crud.get(db, quotation_id)
    if not q:
        raise HTTPException(status_code=404, detail="报价单不存在")

    if q.status not in EDITABLE_STATUSES:
        raise HTTPException(status_code=400, detail="仅草稿和已发送状态的报价单可编辑")

    # Status transition validation
    if quotation_in.status and q.status != quotation_in.status:
        transitions = {
            "draft": {"sent"},
            "sent": {"accepted", "rejected", "expired"},
        }
        allowed = transitions.get(q.status, set())
        if quotation_in.status not in allowed:
            raise HTTPException(
                status_code=400,
                detail=f"报价单状态不能从 '{q.status}' 变更为 '{quotation_in.status}'",
            )

    q = await quotation_crud.update(db, q, quotation_in)
    return QuotationResponse.model_validate(q)


@router.delete("/{quotation_id}")
async def delete_quotation(
    quotation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = await quotation_crud.get(db, quotation_id)
    if not q:
        raise HTTPException(status_code=404, detail="报价单不存在")
    if q.status != "draft":
        raise HTTPException(status_code=400, detail="仅草稿状态可删除")
    await quotation_crud.remove(db, quotation_id)
    return {"message": "报价单已删除"}


@router.post("/{quotation_id}/convert-to-contract", response_model=QuotationResponse)
async def convert_to_contract(
    quotation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = await quotation_crud.get(db, quotation_id)
    if not q:
        raise HTTPException(status_code=404, detail="报价单不存在")
    if q.status != "accepted":
        raise HTTPException(status_code=400, detail="仅已接受的报价单可转为合同")
    if q.contract_id:
        raise HTTPException(status_code=400, detail="该报价单已转为合同")

    # Generate contract number and create contract
    contract_number = await contract_crud.generate_contract_no(db)
    from app.models.contract import Contract
    new_contract = Contract(
        contract_no=contract_number,
        customer_id=q.customer_id,
        title=q.title,
        amount=q.amount,
        status="draft",
    )
    db.add(new_contract)
    await db.flush()  # Ensure new_contract.id is populated

    # Lock quotation to contract
    q.contract_id = new_contract.id
    db.add(q)
    await db.flush()
    await db.commit()
    await db.refresh(q)
    await db.refresh(new_contract)
    return QuotationResponse.model_validate(q)
