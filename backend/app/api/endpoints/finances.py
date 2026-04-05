from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import date

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.finance import FinanceRecord
from app.crud import finance as finance_crud
from app.crud import changelog as changelog_crud
from app.schemas.finance import (
    FinanceRecordCreate,
    FinanceRecordUpdate,
    FinanceRecordResponse,
    FinanceRecordListResponse,
    MonthlySummary,
    CategoryBreakdown,
    DashboardMetrics,
    FundingSourceBreakdown,
)

router = APIRouter()


@router.get("", response_model=FinanceRecordListResponse)
async def list_finance_records(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    type: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    filters = {}
    if type:
        filters["type"] = type
    if category:
        filters["category"] = category
    if status:
        filters["status"] = status

    items, total = await finance_crud.finance_record.list(db, skip=skip, limit=limit, filters=filters)
    return FinanceRecordListResponse(
        items=[FinanceRecordResponse.model_validate(f) for f in items],
        total=total,
        page=(skip // limit) + 1,
        page_size=limit,
    )


@router.post("", response_model=FinanceRecordResponse, status_code=201)
async def create_finance_record(
    record_in: FinanceRecordCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    if record_in.invoice_no:
        existing = await db.execute(
            select(FinanceRecord).where(
                FinanceRecord.invoice_no == record_in.invoice_no, FinanceRecord.is_deleted == False
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="发票号码已存在")

    # FIN-006: expense must have funding_source
    if record_in.type == "expense" and not record_in.funding_source:
        raise HTTPException(status_code=400, detail="支出记录必须填写资金来源")

    # FIN-007: personal_advance/loan must have business_note and settlement_status
    if record_in.funding_source in ("personal_advance", "loan") and not record_in.business_note:
        raise HTTPException(status_code=400, detail="个人垫付/借款必须填写业务说明")

    if record_in.funding_source in ("personal_advance", "loan") and not record_in.settlement_status:
        raise HTTPException(status_code=400, detail="个人垫付/借款必须填写结算状态")

    # FIN-008: related_record requires related_note
    if record_in.related_record_id and not record_in.related_note:
        raise HTTPException(status_code=400, detail="关联记录时必须填写关联说明")

    # FIN-009: related_record must exist
    if record_in.related_record_id:
        target = await db.execute(
            select(FinanceRecord).where(
                FinanceRecord.id == record_in.related_record_id,
                FinanceRecord.is_deleted == False,
            )
        )
        if not target.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="关联记录不存在")

    record = await finance_crud.finance_record.create(db, record_in)
    return FinanceRecordResponse.model_validate(record)


@router.put("/{record_id}", response_model=FinanceRecordResponse)
async def update_finance_record(
    record_id: int,
    record_in: FinanceRecordUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = await finance_crud.finance_record.get(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="财务记录不存在")

    if record_in.invoice_no and record_in.invoice_no != record.invoice_no:
        existing = await db.execute(
            select(FinanceRecord).where(
                FinanceRecord.invoice_no == record_in.invoice_no,
                FinanceRecord.is_deleted == False,
                FinanceRecord.id != record_id,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="发票号码已存在")

    # Merge update data for validation (use new values or fall back to existing)
    effective_type = record_in.type if record_in.type is not None else record.type
    effective_funding = record_in.funding_source if record_in.funding_source is not None else record.funding_source

    # FIN-006: expense must have funding_source
    if effective_type == "expense" and not effective_funding:
        raise HTTPException(status_code=400, detail="支出记录必须填写资金来源")

    # FIN-007: personal_advance/loan must have business_note
    if effective_funding in ("personal_advance", "loan"):
        effective_note = record_in.business_note if record_in.business_note is not None else record.business_note
        if not effective_note:
            raise HTTPException(status_code=400, detail="个人垫付/借款必须填写业务说明")
        effective_settlement = (
            record_in.settlement_status if record_in.settlement_status is not None else record.settlement_status
        )
        if not effective_settlement:
            raise HTTPException(status_code=400, detail="个人垫付/借款必须填写结算状态")

    # FIN-008: related_record requires related_note
    if record_in.related_record_id and not record_in.related_note:
        raise HTTPException(status_code=400, detail="关联记录时必须填写关联说明")

    # FIN-009: no self-reference and target must exist
    if record_in.related_record_id:
        if record_in.related_record_id == record_id:
            raise HTTPException(status_code=400, detail="不允许自关联")
        target = await db.execute(
            select(FinanceRecord).where(
                FinanceRecord.id == record_in.related_record_id,
                FinanceRecord.is_deleted == False,
            )
        )
        if not target.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="关联记录不存在")

    # Save old values before update
    update_data = record_in.model_dump(exclude_unset=True)
    old_values = {field: getattr(record, field, None) for field in update_data}

    record = await finance_crud.finance_record.update(db, record, record_in)

    # Record change logs
    for field, new_val in update_data.items():
        old_val = old_values[field]
        if old_val != new_val:
            await changelog_crud.create_changelog(
                db,
                "finance_record",
                record.id,
                field,
                str(old_val) if old_val is not None else None,
                str(new_val) if new_val is not None else None,
                changed_by=current_user.id,
            )
    await db.commit()

    return FinanceRecordResponse.model_validate(record)


@router.get("/stats/monthly", response_model=MonthlySummary)
async def get_monthly_summary(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    summary = await finance_crud.finance_record.get_monthly_summary(db, year, month)
    return MonthlySummary(**summary)


@router.get("/stats/categories", response_model=CategoryBreakdown)
async def get_category_breakdown(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    breakdown = await finance_crud.finance_record.get_category_breakdown(db, year, month)
    return CategoryBreakdown(categories=breakdown)


@router.get("/stats/accounts-receivable")
async def get_accounts_receivable(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    amount = await finance_crud.finance_record.get_accounts_receivable(db)
    return {"accounts_receivable": amount}


@router.get("/stats/funding-source", response_model=FundingSourceBreakdown)
async def get_funding_source_summary(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    summary = await finance_crud.finance_record.get_funding_source_summary(db, year, month)
    return FundingSourceBreakdown(**summary)
