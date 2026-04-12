"""v1.9 固定成本工具——CRUD、月汇总（业务视角，不摊销）。"""

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    FIXED_COST_PERIOD_WHITELIST,
    FIXED_COST_CATEGORY_WHITELIST,
)
from app.core.logging import get_logger

logger = get_logger("fixed_cost_utils")


def validate_fixed_cost_dates(
    effective_date: date, end_date: date | None
) -> bool:
    """校验 end_date >= effective_date。end_date 为 None 时合法。"""
    if end_date is None:
        return True
    return end_date >= effective_date


def is_cost_active_in_period(
    effective_date: date,
    end_date: date | None,
    period_start: date,
    period_end: date,
) -> bool:
    """判断成本条目是否在指定月份有效（零章 0.3 规则）。"""
    if effective_date > period_end:
        return False
    if end_date is not None and end_date < period_start:
        return False
    return True


def _parse_period_dates(accounting_period: str) -> tuple[date, date]:
    """从 YYYY-MM 字符串解析出 period_start 和 period_end。"""
    from datetime import timedelta
    year, month = map(int, accounting_period.split("-"))
    period_start = date(year, month, 1)
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    period_end = next_month - timedelta(days=1)
    return period_start, period_end


def _serialize_cost_items(active_costs: list) -> list[dict]:
    """序列化成本条目列表。"""
    return [
        {
            "id": c.id,
            "name": c.name,
            "category": c.category,
            "amount": float(c.amount),
            "period": c.period,
            "effective_date": c.effective_date.isoformat(),
            "end_date": c.end_date.isoformat() if c.end_date else None,
            "project_id": c.project_id,
        }
        for c in active_costs
    ]


async def get_monthly_fixed_costs(
    db: AsyncSession, accounting_period: str
) -> dict[str, Any]:
    """按零章 0.3 规则返回指定月份有效固定成本汇总（原始金额，不摊销）。"""
    from app.models.fixed_cost import FixedCost

    period_start, period_end = _parse_period_dates(accounting_period)

    stmt = select(FixedCost).where(FixedCost.effective_date <= period_end)
    result = await db.execute(stmt)
    all_costs = result.scalars().all()

    active_costs = [
        c for c in all_costs
        if is_cost_active_in_period(c.effective_date, c.end_date, period_start, period_end)
    ]

    total_amount = sum(Decimal(str(c.amount)) for c in active_costs)
    by_category: dict[str, float] = {}
    for c in active_costs:
        by_category[c.category] = by_category.get(c.category, 0) + float(c.amount)

    return {
        "accounting_period": accounting_period,
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "total_amount": float(total_amount),
        "by_category": by_category,
        "items": _serialize_cost_items(active_costs),
    }


async def get_project_fixed_costs_total(
    db: AsyncSession, project_id: int
) -> Decimal:
    """返回关联到指定项目的固定成本原始金额之和。"""
    from app.models.fixed_cost import FixedCost

    stmt = select(func.coalesce(func.sum(FixedCost.amount), 0)).where(
        FixedCost.project_id == project_id,
    )
    result = await db.execute(stmt)
    return Decimal(str(result.scalar()))
