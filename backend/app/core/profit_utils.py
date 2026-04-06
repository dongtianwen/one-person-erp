"""v1.4 项目利润核算核心函数——可独立于 FastAPI 应用直接调用和测试。"""
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finance import FinanceRecord
from app.models.contract import Contract
from app.core.constants import DECIMAL_PLACES


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
