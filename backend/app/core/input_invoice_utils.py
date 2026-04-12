"""v1.9 进项发票工具——金额计算、项目汇总、分类统计。"""

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.input_invoice import InputInvoice

logger = get_logger("input_invoice_utils")


def calculate_input_invoice_amount(
    amount_excluding_tax: Decimal, tax_rate: Decimal
) -> dict[str, Decimal]:
    """返回 {tax_amount, total_amount}，四舍五入到 2 位小数。"""
    tax_amount = round(amount_excluding_tax * tax_rate, 2)
    total_amount = round(amount_excluding_tax + tax_amount, 2)
    return {"tax_amount": tax_amount, "total_amount": total_amount}


async def get_project_input_invoice_total(
    db: AsyncSession, project_id: int
) -> Decimal:
    """返回项目关联进项发票含税金额之和。"""
    stmt = select(func.coalesce(func.sum(InputInvoice.total_amount), 0)).where(
        InputInvoice.project_id == project_id,
    )
    result = await db.execute(stmt)
    return Decimal(str(result.scalar()))


async def get_input_invoice_summary(
    db: AsyncSession,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    """按类别汇总进项发票。"""
    stmt = select(
        InputInvoice.category,
        func.count(InputInvoice.id).label("count"),
        func.coalesce(func.sum(InputInvoice.total_amount), 0).label("total"),
    )

    if start_date:
        stmt = stmt.where(InputInvoice.invoice_date >= date.fromisoformat(start_date))
    if end_date:
        stmt = stmt.where(InputInvoice.invoice_date <= date.fromisoformat(end_date))

    stmt = stmt.group_by(InputInvoice.category)
    result = await db.execute(stmt)
    rows = result.fetchall()

    total_amount = Decimal("0")
    by_category: dict[str, Any] = {}
    for row in rows:
        cat_total = Decimal(str(row.total))
        total_amount += cat_total
        by_category[row.category] = {
            "count": row.count,
            "total_amount": float(cat_total),
        }

    return {
        "total_amount": float(total_amount),
        "total_count": sum(r.count for r in rows),
        "by_category": by_category,
    }
