from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.crud import customer as customer_crud
from app.schemas.customer import CustomerCreate, CustomerUpdate, CustomerResponse, CustomerListResponse, CustomerDetailResponse
from app.core.customer_utils import calculate_customer_lifetime_value

router = APIRouter()


@router.get("", response_model=CustomerListResponse)
async def list_customers(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    source: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    filters = {}
    if status:
        filters["status"] = status
    if source:
        filters["source"] = source

    items, total = await customer_crud.customer.list(db, skip=skip, limit=limit, filters=filters)

    if search:
        search_lower = search.lower()
        items = [
            c
            for c in items
            if search_lower in (c.name or "").lower()
            or search_lower in (c.phone or "").lower()
            or search_lower in (c.company or "").lower()
        ]
        total = len(items)

    return CustomerListResponse(
        items=[CustomerResponse.model_validate(c) for c in items],
        total=total,
        page=(skip // limit) + 1,
        page_size=limit,
    )


@router.get("/{customer_id}", response_model=CustomerDetailResponse)
async def get_customer(
    customer_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    from sqlalchemy.orm import selectinload
    from app.models.project import Project
    from app.models.contract import Contract

    customer = await customer_crud.customer.get(db, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")

    proj_result = await db.execute(
        select(Project).where(Project.customer_id == customer_id, Project.is_deleted == False)
    )
    projects = proj_result.scalars().all()

    contract_result = await db.execute(
        select(Contract).where(Contract.customer_id == customer_id, Contract.is_deleted == False)
    )
    contracts = contract_result.scalars().all()

    # v1.4: 客户生命周期价值
    ltv_data = await calculate_customer_lifetime_value(customer_id, db)

    return CustomerDetailResponse(
        customer=CustomerResponse.model_validate(customer),
        projects=[
            {"id": p.id, "name": p.name, "status": p.status, "budget": p.budget, "progress": p.progress, "start_date": str(p.start_date) if p.start_date else None, "end_date": str(p.end_date) if p.end_date else None}
            for p in projects
        ],
        contracts=[
            {"id": c.id, "contract_no": c.contract_no, "title": c.title, "amount": c.amount, "status": c.status, "signed_date": str(c.signed_date) if c.signed_date else None, "start_date": str(c.start_date) if c.start_date else None, "end_date": str(c.end_date) if c.end_date else None}
            for c in contracts
        ],
        lifetime_value={
            "customer_id": customer_id,
            "customer_name": customer.name,
            "total_contract_amount": float(ltv_data["total_contract_amount"]),
            "total_received_amount": float(ltv_data["total_received_amount"]),
            "project_count": ltv_data["project_count"],
            "avg_project_amount": float(ltv_data["avg_project_amount"]) if ltv_data["avg_project_amount"] is not None else None,
            "first_cooperation_date": str(ltv_data["first_cooperation_date"]) if ltv_data["first_cooperation_date"] else None,
            "last_cooperation_date": str(ltv_data["last_cooperation_date"]) if ltv_data["last_cooperation_date"] else None,
            "currency": "CNY",
        },
    )


@router.post("", response_model=CustomerResponse, status_code=201)
async def create_customer(
    customer_in: CustomerCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    existing = await customer_crud.customer.get_by_company_and_contact(
        db, customer_in.company or "", customer_in.contact_person or ""
    )
    if existing and customer_in.company and customer_in.contact_person:
        raise HTTPException(status_code=400, detail="该客户已存在")

    customer = await customer_crud.customer.create(db, customer_in)
    return CustomerResponse.model_validate(customer)


@router.put("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: int,
    customer_in: CustomerUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    customer = await customer_crud.customer.get(db, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")

    if customer_in.status == "lost" and not customer_in.lost_reason:
        raise HTTPException(status_code=400, detail="客户流失必须填写原因")

    customer = await customer_crud.customer.update(db, customer, customer_in)
    return CustomerResponse.model_validate(customer)


@router.get("/{customer_id}/lifetime-value")
async def get_customer_lifetime_value(
    customer_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """FR-402: 客户生命周期价值接口"""
    customer = await customer_crud.customer.get(db, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")

    ltv_data = await calculate_customer_lifetime_value(customer_id, db)
    return {
        "customer_id": customer_id,
        "customer_name": customer.name,
        "total_contract_amount": float(ltv_data["total_contract_amount"]),
        "total_received_amount": float(ltv_data["total_received_amount"]),
        "project_count": ltv_data["project_count"],
        "avg_project_amount": float(ltv_data["avg_project_amount"]) if ltv_data["avg_project_amount"] is not None else None,
        "first_cooperation_date": str(ltv_data["first_cooperation_date"]) if ltv_data["first_cooperation_date"] else None,
        "last_cooperation_date": str(ltv_data["last_cooperation_date"]) if ltv_data["last_cooperation_date"] else None,
        "currency": "CNY",
    }


@router.delete("/{customer_id}")
async def delete_customer(
    customer_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    customer = await customer_crud.customer.get(db, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")

    has_associations = await customer_crud.customer.has_associations(db, customer_id)
    if has_associations:
        raise HTTPException(status_code=400, detail="该客户有关联项目/合同，无法删除")

    await customer_crud.customer.remove(db, customer_id)
    return {"message": "客户已删除"}


@router.get("/stats/status")
async def get_customer_stats_by_status(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    return await customer_crud.customer.get_stats_by_status(db)


@router.get("/stats/source")
async def get_customer_stats_by_source(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    return await customer_crud.customer.get_stats_by_source(db)
