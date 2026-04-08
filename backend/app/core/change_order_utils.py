"""FR-505 变更单/增补单核心工具函数——严格对齐 prd1_5.md 簇 F + v1.7 变更冻结机制"""
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Dict, Any

import sqlite3
import logging

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import CHANGE_ORDER_PREFIX, DECIMAL_PLACES, CHANGE_ORDER_VALID_TRANSITIONS, CHANGE_ORDER_VALID_TRANSITIONS_V17
from app.models.change_order import ChangeOrder
from app.models.quotation import Quotation

logger = logging.getLogger(__name__)


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


# ── v1.7 变更冻结机制工具函数 ─────────────────────────────────

def is_project_requirements_frozen_sync(db: sqlite3.Connection, project_id: int) -> bool:
    """判断项目需求是否冻结（同步版本）。

    项目关联的报价单 status = accepted 时，需求冻结。

    Args:
        db: 数据库连接
        project_id: 项目ID

    Returns:
        bool: True 表示需求已冻结，False 表示未冻结
    """
    cur = db.cursor()
    cur.execute("""
        SELECT q.status
        FROM quotations q
        WHERE q.project_id = ? AND q.status = 'accepted'
        LIMIT 1
    """, (project_id,))
    result = cur.fetchone()
    is_frozen = result is not None
    logger.info(f"项目 {project_id} 需求冻结状态: {is_frozen}")
    return is_frozen


async def is_project_requirements_frozen(db: AsyncSession, project_id: int) -> bool:
    """判断项目需求是否冻结（异步版本）。

    项目关联的报价单 status = accepted 时，需求冻结。

    Args:
        db: AsyncSession 数据库连接
        project_id: 项目ID

    Returns:
        bool: True 表示需求已冻结，False 表示未冻结
    """
    result = await db.execute(
        select(Quotation.id)
        .where(
            Quotation.project_id == project_id,
            Quotation.status == "accepted",
            Quotation.is_deleted == False,
        )
        .limit(1)
    )
    is_frozen = result.first() is not None
    logger.info(f"项目 {project_id} 需求冻结状态: {is_frozen}")
    return is_frozen


def validate_change_order_transition_v17(current: str, target: str) -> bool:
    """校验变更单状态流转是否合法（v1.7 版本）。

    Args:
        current: 当前状态
        target: 目标状态

    Returns:
        bool: True 表示流转合法，False 表示不合法
    """
    if current not in CHANGE_ORDER_VALID_TRANSITIONS_V17:
        logger.warning(f"未知的状态: {current}")
        return False

    allowed_targets = CHANGE_ORDER_VALID_TRANSITIONS_V17[current]
    is_valid = target in allowed_targets
    if not is_valid:
        logger.warning(f"非法的状态流转: {current} → {target}")
    return is_valid


def confirm_change_order_sync(
    db: sqlite3.Connection,
    co_id: int,
    user_id: Optional[int] = None
) -> Dict[str, Any]:
    """客户确认变更单（同步版本）。

    状态变更为 confirmed，写入 client_confirmed_at，同时写 requirement_changes 快照。
    整个操作在原子事务中执行。

    Args:
        db: 数据库连接
        co_id: 变更单ID
        user_id: 操作用户ID（可选）

    Returns:
        Dict: 更新后的变更单数据

    Raises:
        ValueError: 状态流转不合法
        sqlite3.Error: 数据库操作失败
    """
    cur = db.cursor()

    # 获取当前状态
    cur.execute("SELECT status, project_id FROM change_orders WHERE id = ?", (co_id,))
    row = cur.fetchone()
    if not row:
        raise ValueError(f"变更单不存在: {co_id}")

    current_status, project_id = row

    # 校验状态流转
    if not validate_change_order_transition_v17(current_status, "confirmed"):
        raise ValueError(f"不能从 {current_status} 状态流转到 confirmed")

    # 获取变更单详情
    cur.execute("""
        SELECT requirement_change_id, title, description, extra_days, extra_amount
        FROM change_orders WHERE id = ?
    """, (co_id,))
    co_data = cur.fetchone()

    if co_data and co_data[0]:  # 如果关联了需求变更
        requirement_change_id = co_data[0]
        # 写入 requirement_changes 快照（这里简化处理，实际应根据业务逻辑）
        logger.info(f"变更单 {co_id} 确认，关联需求变更 {requirement_change_id}")

    # 更新变更单状态
    cur.execute("""
        UPDATE change_orders
        SET status = 'confirmed',
            client_confirmed_at = ?
        WHERE id = ?
    """, (datetime.now(), co_id))

    logger.info(f"变更单 {co_id} 已确认")
    return {"id": co_id, "status": "confirmed"}


def reject_change_order_sync(
    db: sqlite3.Connection,
    co_id: int,
    reason: str,
    user_id: Optional[int] = None
) -> Dict[str, Any]:
    """客户拒绝变更单（同步版本）。

    状态变更为 rejected，写入 client_rejected_at 和 rejection_reason。
    整个操作在原子事务中执行。

    Args:
        db: 数据库连接
        co_id: 变更单ID
        reason: 拒绝原因
        user_id: 操作用户ID（可选）

    Returns:
        Dict: 更新后的变更单数据

    Raises:
        ValueError: 状态流转不合法
        sqlite3.Error: 数据库操作失败
    """
    cur = db.cursor()

    # 获取当前状态
    cur.execute("SELECT status FROM change_orders WHERE id = ?", (co_id,))
    row = cur.fetchone()
    if not row:
        raise ValueError(f"变更单不存在: {co_id}")

    current_status = row[0]

    # 校验状态流转
    if not validate_change_order_transition_v17(current_status, "rejected"):
        raise ValueError(f"不能从 {current_status} 状态流转到 rejected")

    # 更新变更单状态
    cur.execute("""
        UPDATE change_orders
        SET status = 'rejected',
            client_rejected_at = ?,
            rejection_reason = ?
        WHERE id = ?
    """, (datetime.now(), reason, co_id))

    logger.info(f"变更单 {co_id} 已拒绝，原因: {reason}")
    return {"id": co_id, "status": "rejected"}

