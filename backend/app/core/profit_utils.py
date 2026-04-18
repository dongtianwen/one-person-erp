"""v1.4 项目利润核算核心函数 + v1.9 粗利润视图。"""
# v2.2 fix: 优先查询 accepted 状态的报价单获取日费率
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Optional

from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finance import FinanceRecord
from app.models.contract import Contract
from app.models.project import Project
from app.models.quotation import Quotation
from app.core.constants import (
    DECIMAL_PLACES,
    HOURS_PER_DAY,
    GROSS_PROFIT_DECIMAL_PLACES,
    GROSS_MARGIN_DECIMAL_PLACES,
)
from app.core.logging import get_logger

logger = get_logger("profit_utils")


async def calculate_project_income(project_id: int, db: AsyncSession) -> Decimal:
    """
    项目收入 = finance_records 中满足以下全部条件的金额之和：
      record_type = INCOME（即 type='income'）
      status = CONFIRMED 或 PAID
      related_contract_id 对应合同的 project_id = 该项目 ID
    无符合记录时返回 Decimal("0.00")
    """
    result = await db.execute(
        select(func.coalesce(func.sum(FinanceRecord.amount), 0)).where(
            FinanceRecord.type == "income",
            FinanceRecord.status.in_(["confirmed", "paid"]),
            FinanceRecord.is_deleted == False,
            FinanceRecord.contract_id.in_(
                select(Contract.id).where(
                    Contract.project_id == project_id,
                    Contract.is_deleted == False,
                )
            ),
        )
    )
    return Decimal(str(round(result.scalar(), DECIMAL_PLACES)))


async def calculate_project_cost(project_id: int, db: AsyncSession) -> Decimal:
    """
    项目成本 = finance_records 中满足以下全部条件的金额之和：
      record_type = EXPENSE（即 type='expense'）
      status = CONFIRMED 或 PAID
      related_project_id = 该项目 ID
    无符合记录时返回 Decimal("0.00")
    """
    result = await db.execute(
        select(func.coalesce(func.sum(FinanceRecord.amount), 0)).where(
            FinanceRecord.type == "expense",
            FinanceRecord.status.in_(["confirmed", "paid"]),
            FinanceRecord.is_deleted == False,
            FinanceRecord.related_project_id == project_id,
        )
    )
    return Decimal(str(round(result.scalar(), DECIMAL_PLACES)))


async def calculate_project_profit(project_id: int, db: AsyncSession) -> dict:
    """
    返回：
      income: Decimal（项目收入）
      cost: Decimal（项目成本）
      profit: Decimal（利润 = 收入 - 成本）
      profit_margin: Decimal | None（利润率 %，收入为 0 时返回 None）
    所有金额 round(x, 2)
    """
    income = await calculate_project_income(project_id, db)
    cost = await calculate_project_cost(project_id, db)
    profit = (income - cost).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    profit_margin: Optional[Decimal] = None
    if income > 0:
        profit_margin = (profit / income * 100).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    return {
        "income": income,
        "cost": cost,
        "profit": profit,
        "profit_margin": profit_margin,
    }


# ── v1.9 粗利润视图（新口径：实收 - 工时/固定/进项）──────────────


async def get_project_labor_cost(db: AsyncSession, project_id: int) -> dict:
    """v1.9 工时成本计算。

    公式：labor_cost = round((hours_total / HOURS_PER_DAY) * daily_rate, 2)
    HOURS_PER_DAY 为常量，禁止硬编码。
    """
    # 工时总计
    stmt_hours = select(
        func.coalesce(func.sum(text("hours_spent")), 0)
    ).select_from(text("work_hour_logs")).where(
        text("project_id = :pid"),
    ).params(pid=project_id)
    result = await db.execute(stmt_hours)
    hours_total = Decimal(str(result.scalar()))

    # 获取关联报价单的 daily_rate（优先 accepted 状态）
    stmt_quote = select(Quotation.daily_rate).where(
        Quotation.project_id == project_id,
        Quotation.status == 'accepted',
    ).order_by(Quotation.created_at.desc())
    result_q = await db.execute(stmt_quote)
    row_q = result_q.first()
    daily_rate = Decimal(str(row_q[0])) if row_q and row_q[0] is not None else None

    has_complete_data = hours_total > 0 and daily_rate is not None
    labor_cost: Decimal | None = None
    if has_complete_data:
        labor_cost = round(
            (hours_total / Decimal(str(HOURS_PER_DAY))) * daily_rate,
            GROSS_PROFIT_DECIMAL_PLACES,
        )

    return {
        "labor_cost": labor_cost,
        "hours_total": hours_total,
        "daily_rate": daily_rate,
        "has_complete_data": has_complete_data,
    }


async def _fetch_project_base(db: AsyncSession, project_id: int):
    """获取项目基本信息和合同金额。"""
    stmt_proj = (
        select(Project, Contract.amount)
        .join(Contract, Contract.project_id == Project.id, isouter=True)
        .where(Project.id == project_id)
    )
    result_p = await db.execute(stmt_proj)
    return result_p.first()


async def _fetch_received_amount(db: AsyncSession, project_id: int) -> Decimal:
    """获取项目实收金额。"""
    stmt_rev = select(
        func.coalesce(func.sum(FinanceRecord.amount), 0)
    ).where(
        FinanceRecord.type == "income",
        FinanceRecord.contract_id.in_(
            select(Contract.id).where(Contract.project_id == project_id)
        ),
    )
    result_rev = await db.execute(stmt_rev)
    return Decimal(str(result_rev.scalar()))


def _build_profit_report(
    project_id: int, project: "Project", contract_amount: float,
    received_amount: Decimal, labor_info: dict,
    fixed_cost: Decimal, input_cost: Decimal, warnings: list,
) -> dict[str, Any]:
    """构建粗利润报告字典。"""
    labor_cost = labor_info["labor_cost"]
    total_cost = (labor_cost or Decimal("0")) + fixed_cost + input_cost
    gross_profit = round(received_amount - total_cost, GROSS_PROFIT_DECIMAL_PLACES)
    gross_margin: Decimal | None = None
    if received_amount > 0:
        gross_margin = round(
            gross_profit / received_amount, GROSS_MARGIN_DECIMAL_PLACES,
        )

    return {
        "project_id": project_id,
        "project_name": project.name,
        "calculated_at": datetime.utcnow().isoformat(),
        "revenue": {
            "contract_amount": contract_amount,
            "received_amount": float(received_amount),
            "outstanding_amount": float(
                max(Decimal(str(contract_amount)) - received_amount, Decimal("0"))
            ),
        },
        "cost": {
            "labor_cost": float(labor_cost) if labor_cost is not None else None,
            "labor_hours_actual": float(labor_info["hours_total"]),
            "daily_rate_used": float(labor_info["daily_rate"]) if labor_info["daily_rate"] else None,
            "hours_per_day": HOURS_PER_DAY,
            "fixed_cost_allocated": float(fixed_cost),
            "input_invoice_cost": float(input_cost),
            "total_cost": float(total_cost),
            "has_complete_data": labor_info["has_complete_data"],
        },
        "profit": {
            "gross_profit": float(gross_profit),
            "gross_margin": float(gross_margin) if gross_margin is not None else None,
            "based_on": "received_amount",
        },
        "warnings": warnings,
    }


async def calculate_project_profit_v19(
    db: AsyncSession, project_id: int,
) -> dict[str, Any]:
    """v1.9 计算项目粗利润完整报告。

    数据不完整时返回 warnings 而非报错。
    """
    warnings: list[str] = []
    row_p = await _fetch_project_base(db, project_id)
    if row_p is None:
        return {"error": "project not found"}

    project = row_p[0]
    contract_amount = float(row_p[1] or 0)

    received_amount = await _fetch_received_amount(db, project_id)

    labor_info = await get_project_labor_cost(db, project_id)
    if labor_info["hours_total"] == 0:
        warnings.append("无工时记录")
    elif labor_info["daily_rate"] is None:
        warnings.append("关联报价单无 daily_rate")

    from app.core.fixed_cost_utils import get_project_fixed_costs_total
    from app.core.input_invoice_utils import get_project_input_invoice_total
    fixed_cost = await get_project_fixed_costs_total(db, project_id)
    input_cost = await get_project_input_invoice_total(db, project_id)

    return _build_profit_report(
        project_id, project, contract_amount,
        received_amount, labor_info, fixed_cost, input_cost, warnings,
    )


async def refresh_project_profit_cache(
    db: AsyncSession, project_id: int,
) -> dict[str, Any]:
    """v1.9 写入 projects 缓存字段，原子事务。"""
    report = await calculate_project_profit_v19(db, project_id)
    if "error" in report:
        return report

    stmt = select(Project).where(Project.id == project_id)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if project is None:
        return {"error": "project not found"}

    project.cached_revenue = Decimal(str(report["revenue"]["received_amount"]))
    project.cached_labor_cost = (
        Decimal(str(report["cost"]["labor_cost"]))
        if report["cost"]["labor_cost"] is not None else None
    )
    project.cached_fixed_cost = Decimal(str(report["cost"]["fixed_cost_allocated"]))
    project.cached_input_cost = Decimal(str(report["cost"]["input_invoice_cost"]))
    project.cached_gross_profit = Decimal(str(report["profit"]["gross_profit"]))
    project.cached_gross_margin = (
        Decimal(str(report["profit"]["gross_margin"]))
        if report["profit"]["gross_margin"] is not None else None
    )
    project.profit_cache_updated_at = datetime.utcnow()

    await db.commit()
    logger.info("项目利润缓存刷新 | project_id=%d", project_id)
    return report


async def get_profit_overview(db: AsyncSession) -> list[dict[str, Any]]:
    """v1.9 所有项目粗利润列表，优先读缓存。"""
    stmt = select(Project)
    result = await db.execute(stmt)
    projects = result.scalars().all()

    overview = []
    for p in projects:
        if p.cached_gross_profit is not None:
            overview.append({
                "project_id": p.id,
                "project_name": p.name,
                "revenue": float(p.cached_revenue or 0),
                "total_cost": float(
                    (p.cached_labor_cost or 0) + (p.cached_fixed_cost or 0) + (p.cached_input_cost or 0)
                ),
                "gross_profit": float(p.cached_gross_profit),
                "gross_margin": float(p.cached_gross_margin) if p.cached_gross_margin else None,
                "cached_at": p.profit_cache_updated_at.isoformat() if p.profit_cache_updated_at else None,
            })
        else:
            # 缓存为空，实时计算
            report = await calculate_project_profit_v19(db, p.id)
            if "error" not in report:
                overview.append({
                    "project_id": p.id,
                    "project_name": p.name,
                    "revenue": report["revenue"]["received_amount"],
                    "total_cost": report["cost"]["total_cost"],
                    "gross_profit": report["profit"]["gross_profit"],
                    "gross_margin": report["profit"]["gross_margin"],
                    "cached_at": None,
                })
    return overview
