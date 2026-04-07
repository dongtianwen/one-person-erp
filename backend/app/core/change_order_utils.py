"""FR-505 变更单/增补单核心工具函数——严格对齐 prd1_5.md 簇 F"""
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import CHANGE_ORDER_PREFIX, DECIMAL_PLACES
from app.models.change_order import ChangeOrder


async def generate_change_order_no(db: AsyncSession) -> str:
    """
    格式：BG-YYYYMMDD-序号（3 位补零）。
    当日序号 = 当日已有变更单数量 + 1。
    必须在调用方事务中执行，防止并发重复。
    """
    today = date.today()
    date_str = today.strftime("%Y%m%d")
    prefix = f"{CHANGE_ORDER_PREFIX}-{date_str}-"

    result = await db.execute(
        select(func.count(ChangeOrder.id)).where(ChangeOrder.order_no.like(f"{prefix}%"))
    )
    count = result.scalar() or 0
    seq = count + 1
    return f"{prefix}{seq:03d}"


def validate_status_transition(current: str, target: str) -> bool:
    """
    使用 CHANGE_ORDER_VALID_TRANSITIONS 校验状态流转是否合法。
    返回 True 表示合法，False 表示非法。
    """
    from app.core.constants import CHANGE_ORDER_VALID_TRANSITIONS
    allowed = CHANGE_ORDER_VALID_TRANSITIONS.get(current, [])
    return target in allowed


async def calculate_actual_receivable(contract_id: int, db: AsyncSession) -> dict:
    """
    confirmed_total: change_orders 中 status IN (confirmed, in_progress, completed) 的 amount 之和
    actual_receivable: round(contracts.amount + confirmed_total, 2)
    返回：{"confirmed_total": Decimal, "actual_receivable": Decimal}
    """
    from app.models.contract import Contract

    # confirmed_total
    result = await db.execute(
        select(func.coalesce(func.sum(ChangeOrder.amount), 0)).where(
            ChangeOrder.contract_id == contract_id,
            ChangeOrder.status.in_(["confirmed", "in_progress", "completed"]),
        )
    )
    confirmed_total = Decimal(str(result.scalar() or 0)).quantize(
        Decimal(10) ** -DECIMAL_PLACES, rounding=ROUND_HALF_UP
    )

    # contract amount
    contract = await db.get(Contract, contract_id)
    contract_amount = Decimal(str(contract.amount if contract and contract.amount else 0))

    actual_receivable = (contract_amount + confirmed_total).quantize(
        Decimal(10) ** -DECIMAL_PLACES, rounding=ROUND_HALF_UP
    )

    return {"confirmed_total": confirmed_total, "actual_receivable": actual_receivable}
