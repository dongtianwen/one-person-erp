import logging
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import date

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.core.logging import get_logger

logger = get_logger("finances")
from app.models.finance import FinanceRecord
from app.models.project import Project
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
from app.core.constants import OUTSOURCE_CATEGORY, DECIMAL_PLACES
from app.core.finance_utils import calculate_tax_amount

router = APIRouter()


def _is_invoice_no_empty(invoice_no: Optional[str]) -> bool:
    """判断发票号码是否为空（NULL 或空字符串）。"""
    return invoice_no is None or invoice_no.strip() == ""


def _validate_outsource_fields(data: dict) -> None:
    """
    FR-302: 当 category == outsourcing 时校验三个必填字段；
    当 category != outsourcing 时强制三个字段置 NULL。
    直接修改 data dict。
    """
    if data.get("category") == OUTSOURCE_CATEGORY:
        if not data.get("outsource_name"):
            raise HTTPException(status_code=422, detail="外包费用必须填写外包方姓名")
        if data.get("has_invoice") is None:
            raise HTTPException(status_code=422, detail="外包费用必须填写是否取得发票")
        if not data.get("tax_treatment"):
            raise HTTPException(status_code=422, detail="外包费用必须填写税务处理方式")
    else:
        # 非外包：强制置 NULL
        data["outsource_name"] = None
        data["has_invoice"] = None
        data["tax_treatment"] = None


def _validate_invoice_fields(data: dict) -> None:
    """
    FR-303: 当 invoice_no 不为空时校验发票字段并计算 tax_amount；
    当 invoice_no 为空时强制四个发票字段置 NULL。
    直接修改 data dict。
    """
    if not _is_invoice_no_empty(data.get("invoice_no")):
        if not data.get("invoice_direction"):
            raise HTTPException(status_code=422, detail="填写发票号码时必须填写发票方向")
        if not data.get("invoice_type"):
            raise HTTPException(status_code=422, detail="填写发票号码时必须填写发票类型")
        if data.get("tax_rate") is None:
            raise HTTPException(status_code=422, detail="填写发票号码时必须填写税率")
        # 后端计算 tax_amount
        amount = Decimal(str(data.get("amount", 0)))
        tax_rate = Decimal(str(data["tax_rate"]))
        data["tax_amount"] = calculate_tax_amount(amount, tax_rate)
    else:
        # 无发票号码：强制置 NULL
        data["invoice_direction"] = None
        data["invoice_type"] = None
        data["tax_rate"] = None
        data["tax_amount"] = None


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

    # v1.3 校验与字段清理
    data = record_in.model_dump()
    _validate_outsource_fields(data)
    _validate_invoice_fields(data)

    # v1.4 校验 related_project_id
    if data.get("related_project_id") is not None:
        proj = await db.execute(select(Project).where(Project.id == data["related_project_id"], Project.is_deleted == False))
        if not proj.scalar_one_or_none():
            raise HTTPException(status_code=422, detail="关联项目不存在")

    record = await finance_crud.finance_record.create_with_data(db, data)
    logger.info("finance_record created | id=%s type=%s amount=%s", record.id, record.type, record.amount)
    return FinanceRecordResponse.model_validate(record)


def _merge_effective_fields(record, update_data: dict) -> dict:
    """合并新旧字段值用于校验。"""
    effective = {}
    for field in [
        "type", "amount", "category", "funding_source", "invoice_no",
        "outsource_name", "has_invoice", "tax_treatment",
        "invoice_direction", "invoice_type", "tax_rate",
    ]:
        if field in update_data:
            effective[field] = update_data[field]
        else:
            effective[field] = getattr(record, field, None)
    return effective


def _validate_v1_funding(effective: dict, record, record_in) -> None:
    """校验 v1.1 资金来源 + 关联记录规则。"""
    if effective["type"] == "expense" and not effective["funding_source"]:
        raise HTTPException(status_code=400, detail="支出记录必须填写资金来源")

    if effective["funding_source"] in ("personal_advance", "loan"):
        note = record_in.business_note if record_in.business_note is not None else record.business_note
        if not note:
            raise HTTPException(status_code=400, detail="个人垫付/借款必须填写业务说明")
        settlement = record_in.settlement_status if record_in.settlement_status is not None else record.settlement_status
        if not settlement:
            raise HTTPException(status_code=400, detail="个人垫付/借款必须填写结算状态")


async def _write_changelog(db, record, update_data: dict, old_values: dict, user_id: int) -> None:
    """写入变更日志。"""
    for field, new_val in update_data.items():
        old_val = old_values[field]
        if old_val != new_val:
            await changelog_crud.create_changelog(
                db, "finance_record", record.id, field,
                str(old_val) if old_val is not None else None,
                str(new_val) if new_val is not None else None,
                changed_by=user_id,
            )


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

    update_data = record_in.model_dump(exclude_unset=True)
    effective = _merge_effective_fields(record, update_data)

    _validate_v1_funding(effective, record, record_in)

    if record_in.related_record_id and not record_in.related_note:
        raise HTTPException(status_code=400, detail="关联记录时必须填写关联说明")
    if record_in.related_record_id:
        if record_in.related_record_id == record_id:
            raise HTTPException(status_code=400, detail="不允许自关联")
        target = await db.execute(
            select(FinanceRecord).where(FinanceRecord.id == record_in.related_record_id, FinanceRecord.is_deleted == False)
        )
        if not target.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="关联记录不存在")

    _validate_outsource_fields(effective)
    _validate_invoice_fields(effective)

    # v1.4 校验 related_project_id
    if update_data.get("related_project_id") is not None:
        proj = await db.execute(select(Project).where(Project.id == update_data["related_project_id"], Project.is_deleted == False))
        if not proj.scalar_one_or_none():
            raise HTTPException(status_code=422, detail="关联项目不存在")

    for field in ["outsource_name", "has_invoice", "tax_treatment", "invoice_direction", "invoice_type", "tax_rate", "tax_amount"]:
        update_data[field] = effective.get(field)

    old_values = {field: getattr(record, field, None) for field in update_data}
    record = await finance_crud.finance_record.update_with_data(db, record, update_data)
    await _write_changelog(db, record, update_data, old_values, current_user.id)
    await db.commit()
    logger.info("finance_record updated | id=%s fields=%s", record.id, list(update_data.keys()))
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


@router.get("/tax-summary")
async def get_tax_summary(
    year: int = Query(..., ge=2000, le=2100),
    quarter: int = Query(..., ge=1, le=4),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """FR-303 季度增值税汇总统计"""
    from decimal import Decimal
    from app.core.finance_utils import get_quarter_date_range
    from app.core.constants import INVOICE_DIRECTION_OUTPUT, INVOICE_DIRECTION_INPUT, INVOICE_TYPE_SPECIAL

    start_date, end_date = get_quarter_date_range(year, quarter)

    # 销项税合计：invoice_direction = output 的所有记录
    output_result = await db.execute(
        select(func.coalesce(func.sum(FinanceRecord.tax_amount), 0)).where(
            FinanceRecord.invoice_direction == INVOICE_DIRECTION_OUTPUT,
            FinanceRecord.date >= start_date,
            FinanceRecord.date <= end_date,
            FinanceRecord.is_deleted == False,
        )
    )
    output_tax_total = float(output_result.scalar() or 0)
    output_tax_total = round(output_tax_total, 2)

    # 销项记录数
    output_count_result = await db.execute(
        select(func.count(FinanceRecord.id)).where(
            FinanceRecord.invoice_direction == INVOICE_DIRECTION_OUTPUT,
            FinanceRecord.date >= start_date,
            FinanceRecord.date <= end_date,
            FinanceRecord.is_deleted == False,
        )
    )
    output_count = output_count_result.scalar() or 0

    # 进项税合计：invoice_direction = input AND invoice_type = special
    input_result = await db.execute(
        select(func.coalesce(func.sum(FinanceRecord.tax_amount), 0)).where(
            FinanceRecord.invoice_direction == INVOICE_DIRECTION_INPUT,
            FinanceRecord.invoice_type == INVOICE_TYPE_SPECIAL,
            FinanceRecord.date >= start_date,
            FinanceRecord.date <= end_date,
            FinanceRecord.is_deleted == False,
        )
    )
    input_tax_total = float(input_result.scalar() or 0)
    input_tax_total = round(input_tax_total, 2)

    # 进项记录数（仅专用发票）
    input_count_result = await db.execute(
        select(func.count(FinanceRecord.id)).where(
            FinanceRecord.invoice_direction == INVOICE_DIRECTION_INPUT,
            FinanceRecord.invoice_type == INVOICE_TYPE_SPECIAL,
            FinanceRecord.date >= start_date,
            FinanceRecord.date <= end_date,
            FinanceRecord.is_deleted == False,
        )
    )
    input_count = input_count_result.scalar() or 0

    tax_payable = round(output_tax_total - input_tax_total, 2)
    logger.info("tax_summary | year=%s quarter=%s output=%s input=%s payable=%s", year, quarter, output_tax_total, input_tax_total, tax_payable)

    return {
        "year": year,
        "quarter": quarter,
        "output_tax_total": output_tax_total,
        "input_tax_total": input_tax_total,
        "tax_payable": tax_payable,
        "record_count": {
            "output": output_count,
            "input": input_count,
        },
    }
