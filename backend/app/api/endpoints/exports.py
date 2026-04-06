"""FR-403 数据导出接口。"""

import logging
from datetime import date
from decimal import Decimal
from io import BytesIO
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.customer import Customer
from app.models.project import Project
from app.models.contract import Contract
from app.models.finance import FinanceRecord
from app.core.constants import EXPORT_DATE_FORMAT
from app.core.export_utils import (
    generate_excel,
    generate_pdf,
    get_export_filename,
    EXPORT_TYPES,
    EXPORT_FORMATS,
)
from app.core.profit_utils import calculate_project_profit
from app.core.customer_utils import calculate_customer_lifetime_value
from app.core.logging import get_logger

logger = get_logger("export")

router = APIRouter()

STATUS_LABELS = {"pending": "待确认", "confirmed": "已确认", "invoiced": "已开票", "paid": "已付款", "cancelled": "已取消"}
FUNDING_SOURCE_LABELS = {
    "company_account": "对公账户",
    "personal_advance": "个人垫付",
    "reimbursement": "报销",
    "loan": "借款",
    "loan_repayment": "借款归还",
    "other": "其他",
}
CATEGORY_LABELS = {
    "development": "开发费", "design": "设计费", "maintenance": "维护费", 
    "server": "服务器", "office": "办公", "other": "其他", "outsourcing": "外包费用"
}


class ExportRequest(BaseModel):
    format: str  # xlsx | pdf
    year: int
    month: Optional[int] = None
    quarter: Optional[int] = None

    @field_validator("format")
    @classmethod
    def validate_format(cls, v: str) -> str:
        if v not in EXPORT_FORMATS:
            raise ValueError(f"不支持的导出格式：{v}，仅支持 {', '.join(EXPORT_FORMATS)}")
        return v

    @field_validator("year")
    @classmethod
    def validate_year(cls, v: int) -> int:
        if v < 2000 or v > 2100:
            raise ValueError("年份必须在 2000-2100 之间")
        return v

    @field_validator("month")
    @classmethod
    def validate_month(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (v < 1 or v > 12):
            raise ValueError("月份必须在 1-12 之间")
        return v

    @field_validator("quarter")
    @classmethod
    def validate_quarter(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (v < 1 or v > 4):
            raise ValueError("季度必须在 1-4 之间")
        return v


def _validate_params(export_type: str, req: ExportRequest) -> None:
    """校验导出参数。"""
    if export_type not in EXPORT_TYPES:
        raise HTTPException(status_code=422, detail=f"不支持的导出类型：{export_type}")

    if export_type == "tax_ledger":
        if req.quarter is None:
            raise HTTPException(status_code=422, detail="增值税台账必须指定季度(quarter)")
        if req.month is not None:
            raise HTTPException(status_code=422, detail="增值税台账使用季度(quarter)，不能指定月份(month)")
    elif export_type == "finance_report":
        if req.month is None:
            raise HTTPException(status_code=422, detail="月度财务报表必须指定月份(month)")
    # 对于 customers, projects, contracts，不需要 month 或 quarter


async def _fetch_finance_report_data(db: AsyncSession, year: int, month: int) -> dict:
    """获取月度财务报表数据。"""
    from calendar import monthrange

    _, last_day = monthrange(year, month)
    start_date = date(year, month, 1)
    end_date = date(year, month, last_day)

    # 收支明细
    result = await db.execute(
        select(FinanceRecord)
        .where(
            FinanceRecord.date >= start_date,
            FinanceRecord.date <= end_date,
            FinanceRecord.is_deleted == False,
        )
        .order_by(FinanceRecord.date)
    )
    records = result.scalars().all()

    details = []
    for r in records:
        contract_info = ""
        if r.contract_id:
            c_result = await db.execute(select(Contract).where(Contract.id == r.contract_id))
            c = c_result.scalar_one_or_none()
            if c:
                contract_info = c.contract_no
        details.append(
            [
                r.date.strftime(EXPORT_DATE_FORMAT) if r.date else "",
                "收入" if r.type == "income" else "支出",
                CATEGORY_LABELS.get(r.category, r.category) if r.category else "",
                r.amount,
                FUNDING_SOURCE_LABELS.get(r.funding_source, r.funding_source) if r.funding_source else "",
                contract_info,
                r.invoice_no or "",
                STATUS_LABELS.get(r.status, r.status) if r.status else "",
                r.description or r.business_note or "",
            ]
        )

    # 分类汇总
    cat_result = await db.execute(
        select(
            FinanceRecord.category,
            func.coalesce(func.sum(case((FinanceRecord.type == "income", FinanceRecord.amount), else_=0)), 0),
            func.coalesce(func.sum(case((FinanceRecord.type == "expense", FinanceRecord.amount), else_=0)), 0),
        )
        .where(
            FinanceRecord.date >= start_date,
            FinanceRecord.date <= end_date,
            FinanceRecord.is_deleted == False,
        )
        .group_by(FinanceRecord.category)
    )
    category_summary = []
    for row in cat_result.all():
        cat, inc, exp = row
        cat_label = CATEGORY_LABELS.get(cat, cat) if cat else "未分类"
        category_summary.append([cat_label, float(inc), float(exp), round(float(inc) - float(exp), 2)])

    # 资金来源汇总
    fund_result = await db.execute(
        select(
            FinanceRecord.funding_source,
            func.coalesce(func.sum(FinanceRecord.amount), 0),
        )
        .where(
            FinanceRecord.type == "expense",
            FinanceRecord.date >= start_date,
            FinanceRecord.date <= end_date,
            FinanceRecord.is_deleted == False,
        )
        .group_by(FinanceRecord.funding_source)
    )
    funding_summary = []
    for row in fund_result.all():
        src, total = row
        unsettled_result = await db.execute(
            select(func.count(FinanceRecord.id), func.coalesce(func.sum(FinanceRecord.amount), 0)).where(
                FinanceRecord.funding_source == src,
                FinanceRecord.type == "expense",
                FinanceRecord.settlement_status != "settled",
                FinanceRecord.date >= start_date,
                FinanceRecord.date <= end_date,
                FinanceRecord.is_deleted == False,
            )
        )
        unset_count, unset_amount = unsettled_result.one()
        src_label = FUNDING_SOURCE_LABELS.get(src, src) if src else "未指定"
        funding_summary.append([src_label, float(total), unset_count, float(unset_amount)])

    return {"details": details, "category_summary": category_summary, "funding_summary": funding_summary}


async def _fetch_customers_data(db: AsyncSession) -> dict:
    """获取客户列表数据。"""
    result = await db.execute(select(Customer).where(Customer.is_deleted == False))
    customers = result.scalars().all()

    items = []
    for c in customers:
        ltv = await calculate_customer_lifetime_value(c.id, db)
        items.append(
            [
                c.name or "",
                c.contact_person or "",
                c.phone or "",
                c.company or "",
                c.status or "",
                c.source or "",
                ltv["project_count"],
                float(ltv["total_contract_amount"]),
                float(ltv["total_received_amount"]),
                str(ltv["first_cooperation_date"]) if ltv["first_cooperation_date"] else "",
                str(ltv["last_cooperation_date"]) if ltv["last_cooperation_date"] else "",
                c.created_at.strftime(EXPORT_DATE_FORMAT) if c.created_at else "",
            ]
        )
    return {"items": items}


async def _fetch_projects_data(db: AsyncSession) -> dict:
    """获取项目列表数据（含利润）。"""
    result = await db.execute(select(Project).where(Project.is_deleted == False))
    projects = result.scalars().all()

    items = []
    for p in projects:
        profit_data = await calculate_project_profit(p.id, db)
        customer_name = ""
        if p.customer_id:
            c_result = await db.execute(select(Customer).where(Customer.id == p.customer_id))
            c = c_result.scalar_one_or_none()
            if c:
                customer_name = c.name or ""
        items.append(
            [
                p.name or "",
                customer_name,
                p.status or "",
                p.budget if p.budget is not None else "",
                float(profit_data["income"]),
                float(profit_data["cost"]),
                float(profit_data["profit"]),
                float(profit_data["profit_margin"]) if profit_data["profit_margin"] is not None else "",
                p.start_date.strftime(EXPORT_DATE_FORMAT) if p.start_date else "",
                p.end_date.strftime(EXPORT_DATE_FORMAT) if p.end_date else "",
                p.progress if p.progress is not None else "",
            ]
        )
    return {"items": items}


async def _fetch_contracts_data(db: AsyncSession) -> dict:
    """获取合同列表数据。"""
    result = await db.execute(select(Contract).where(Contract.is_deleted == False))
    contracts = result.scalars().all()

    items = []
    for c in contracts:
        customer_name = ""
        if c.customer_id:
            cust_result = await db.execute(select(Customer).where(Customer.id == c.customer_id))
            cust = cust_result.scalar_one_or_none()
            if cust:
                customer_name = cust.name or ""

        project_name = ""
        if c.project_id:
            proj_result = await db.execute(select(Project).where(Project.id == c.project_id))
            proj = proj_result.scalar_one_or_none()
            if proj:
                project_name = proj.name or ""

        received = await db.execute(
            select(func.coalesce(func.sum(FinanceRecord.amount), 0)).where(
                FinanceRecord.contract_id == c.id,
                FinanceRecord.type == "income",
                FinanceRecord.status == "confirmed",
                FinanceRecord.is_deleted == False,
            )
        )
        received_amount = float(received.scalar() or 0)
        receivable = round(c.amount - received_amount, 2)

        items.append(
            [
                c.contract_no or "",
                c.title or "",
                customer_name,
                project_name,
                c.amount,
                received_amount,
                receivable,
                c.status or "",
                c.signed_date.strftime(EXPORT_DATE_FORMAT) if c.signed_date else "",
                c.start_date.strftime(EXPORT_DATE_FORMAT) if c.start_date else "",
                c.end_date.strftime(EXPORT_DATE_FORMAT) if c.end_date else "",
            ]
        )
    return {"items": items}


async def _fetch_tax_ledger_data(db: AsyncSession, year: int, quarter: int) -> dict:
    """获取增值税发票台账数据。"""
    from app.core.finance_utils import get_quarter_date_range

    start_date, end_date = get_quarter_date_range(year, quarter)

    result = await db.execute(
        select(FinanceRecord)
        .where(
            FinanceRecord.invoice_no.isnot(None),
            FinanceRecord.invoice_no != "",
            FinanceRecord.date >= start_date,
            FinanceRecord.date <= end_date,
            FinanceRecord.is_deleted == False,
        )
        .order_by(FinanceRecord.date)
    )
    records = result.scalars().all()

    items = []
    for r in records:
        contract_info = ""
        if r.contract_id:
            c_result = await db.execute(select(Contract).where(Contract.id == r.contract_id))
            c = c_result.scalar_one_or_none()
            if c:
                contract_info = c.contract_no
        items.append(
            [
                r.date.strftime(EXPORT_DATE_FORMAT) if r.date else "",
                r.invoice_no or "",
                "销项"
                if r.invoice_direction == "output"
                else "进项"
                if r.invoice_direction == "input"
                else r.invoice_direction or "",
                r.invoice_type or "",
                r.amount,
                float(r.tax_rate) if r.tax_rate is not None else "",
                float(r.tax_amount) if r.tax_amount is not None else "",
                contract_info,
                r.description or "",
            ]
        )

    # 汇总
    output_tax_result = await db.execute(
        select(func.coalesce(func.sum(FinanceRecord.tax_amount), 0)).where(
            FinanceRecord.invoice_direction == "output",
            FinanceRecord.date >= start_date,
            FinanceRecord.date <= end_date,
            FinanceRecord.is_deleted == False,
        )
    )
    output_tax = float(output_tax_result.scalar() or 0)

    input_tax_result = await db.execute(
        select(func.coalesce(func.sum(FinanceRecord.tax_amount), 0)).where(
            FinanceRecord.invoice_direction == "input",
            FinanceRecord.invoice_type == "special",
            FinanceRecord.date >= start_date,
            FinanceRecord.date <= end_date,
            FinanceRecord.is_deleted == False,
        )
    )
    input_tax = float(input_tax_result.scalar() or 0)

    payable = round(output_tax - input_tax, 2)

    return {
        "items": items,
        "summary": {
            "output_tax": round(output_tax, 2),
            "input_tax": round(input_tax, 2),
            "payable_tax": payable,
        },
    }


@router.post("/{export_type}")
async def export_data(
    export_type: str,
    req: ExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """FR-403: 数据导出接口"""
    _validate_params(export_type, req)

    try:
        # 获取数据
        if export_type == "finance_report":
            data = await _fetch_finance_report_data(db, req.year, req.month)
        elif export_type == "customers":
            data = await _fetch_customers_data(db)
        elif export_type == "projects":
            data = await _fetch_projects_data(db)
        elif export_type == "contracts":
            data = await _fetch_contracts_data(db)
        elif export_type == "tax_ledger":
            data = await _fetch_tax_ledger_data(db, req.year, req.quarter)
        else:
            raise HTTPException(status_code=422, detail=f"不支持的导出类型：{export_type}")

        # 生成文件
        if req.format == "xlsx":
            file_bytes = generate_excel(export_type, data, req.year, req.month, req.quarter)
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        else:
            file_bytes = generate_pdf(export_type, data, req.year, req.month, req.quarter)
            content_type = "application/pdf"

        filename = get_export_filename(export_type, req.format, req.year, req.month, req.quarter)
        encoded_filename = filename.encode("utf-8").decode("latin-1")

        logger.info(
            "export success | type=%s format=%s year=%s month=%s quarter=%s filename=%s",
            export_type,
            req.format,
            req.year,
            req.month,
            req.quarter,
            filename,
        )

        return StreamingResponse(
            BytesIO(file_bytes),
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename={encoded_filename}; filename*=UTF-8''{filename}",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "export failed | type=%s format=%s year=%s month=%s quarter=%s error=%s",
            export_type,
            req.format,
            req.year,
            req.month,
            req.quarter,
            str(e),
        )
        raise HTTPException(status_code=500, detail="导出失败，请重试")
