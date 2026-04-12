"""v1.9 收款逾期预警——里程碑逾期检测与客户风险等级。"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    CUSTOMER_OVERDUE_WARN_THRESHOLD,
    CUSTOMER_OVERDUE_HIGH_THRESHOLD,
    CUSTOMER_OVERDUE_HIGH_RATIO,
)
from app.core.logging import get_logger
from app.models.contract import Contract
from app.models.customer import Customer
from app.models.project import Milestone, Project

logger = get_logger("overdue_utils")


async def get_overdue_milestones(db: AsyncSession) -> list[dict[str, Any]]:
    """只读：返回所有逾期未收款里程碑。

    逾期条件：payment_due_date < 今日 且 payment_status != received。
    """
    today = date.today()
    stmt = (
        select(
            Milestone.id,
            Milestone.title,
            Milestone.payment_amount,
            Milestone.payment_due_date,
            Milestone.payment_status,
            Project.id.label("project_id"),
            Project.name.label("project_name"),
            Customer.id.label("customer_id"),
            Customer.name.label("customer_name"),
        )
        .join(Project, Milestone.project_id == Project.id)
        .join(Customer, Project.customer_id == Customer.id)
        .where(
            Milestone.payment_due_date < today,
            Milestone.payment_status != "received",
        )
        .order_by(Milestone.payment_due_date)
    )
    result = await db.execute(stmt)
    rows = result.fetchall()

    overdue = []
    for row in rows:
        due_date = row.payment_due_date
        overdue_days = (today - due_date).days if due_date else 0
        overdue.append({
            "milestone_id": row.id,
            "milestone_name": row.title,
            "project_id": row.project_id,
            "project_name": row.project_name,
            "customer_id": row.customer_id,
            "customer_name": row.customer_name,
            "payment_amount": float(row.payment_amount or 0),
            "payment_due_date": due_date.isoformat() if due_date else None,
            "overdue_days": overdue_days,
            "payment_status": row.payment_status,
        })
    return overdue


def calculate_customer_risk_level(
    overdue_count: int,
    overdue_amount: Decimal,
    total_contract_amount: Decimal,
) -> str:
    """返回 normal / warning / high，严格按常量阈值。

    规则：
    - normal: overdue_count = 0
    - warning: overdue_count >= WARN_THRESHOLD
    - high: overdue_count >= HIGH_THRESHOLD OR overdue_amount/total >= HIGH_RATIO
    - high 优先级高于 warning
    """
    if overdue_count == 0:
        return "normal"

    # high 判定优先
    if overdue_count >= CUSTOMER_OVERDUE_HIGH_THRESHOLD:
        return "high"

    if (
        total_contract_amount > 0
        and (overdue_amount / total_contract_amount) >= Decimal(str(CUSTOMER_OVERDUE_HIGH_RATIO))
    ):
        return "high"

    if overdue_count >= CUSTOMER_OVERDUE_WARN_THRESHOLD:
        return "warning"

    return "normal"


async def _refresh_single_customer_risk(
    db: AsyncSession, customer: Customer, today: date,
) -> bool:
    """计算并写入单个客户的风险字段，返回是否更新。"""
    stmt_projects = select(Project.id).where(Project.customer_id == customer.id)
    result_projects = await db.execute(stmt_projects)
    project_ids = [row[0] for row in result_projects.fetchall()]

    if not project_ids:
        customer.overdue_milestone_count = 0
        customer.overdue_amount = Decimal("0")
        customer.risk_level = "normal"
        return True

    stmt_overdue = select(
        func.count(Milestone.id).label("cnt"),
        func.coalesce(func.sum(Milestone.payment_amount), 0).label("total"),
    ).where(
        Milestone.project_id.in_(project_ids),
        Milestone.payment_due_date < today,
        Milestone.payment_status != "received",
    )
    result_overdue = await db.execute(stmt_overdue)
    row_overdue = result_overdue.one()
    overdue_count = row_overdue.cnt
    overdue_amount = Decimal(str(row_overdue.total))

    stmt_contracts = select(
        func.coalesce(func.sum(Contract.amount), 0)
    ).where(Contract.customer_id == customer.id)
    result_contracts = await db.execute(stmt_contracts)
    total_contract_amount = Decimal(str(result_contracts.scalar()))

    risk = calculate_customer_risk_level(
        overdue_count, overdue_amount, total_contract_amount,
    )
    customer.overdue_milestone_count = overdue_count
    customer.overdue_amount = overdue_amount
    customer.risk_level = risk
    return True


async def refresh_customer_risk_fields(db: AsyncSession) -> int:
    """批量更新 customers 表风险字段，原子事务，返回更新记录数。"""
    today = date.today()

    stmt_customers = select(Customer)
    result = await db.execute(stmt_customers)
    customers = result.scalars().all()

    updated = 0
    for customer in customers:
        try:
            if await _refresh_single_customer_risk(db, customer, today):
                updated += 1
        except Exception as e:
            logger.error("客户风险刷新失败 | customer_id=%d error=%s", customer.id, e)

    await db.commit()
    logger.info("客户风险字段刷新完成 | updated=%d", updated)
    return updated


async def get_customer_risk_summary(
    db: AsyncSession, customer_id: int,
) -> dict[str, Any]:
    """获取单个客户逾期与风险摘要。"""
    stmt = (
        select(
            Customer.id,
            Customer.name,
            Customer.overdue_milestone_count,
            Customer.overdue_amount,
            Customer.risk_level,
        )
        .where(Customer.id == customer_id)
    )
    result = await db.execute(stmt)
    row = result.one_or_none()
    if row is None:
        return {}

    return {
        "customer_id": row.id,
        "customer_name": row.name,
        "overdue_count": row.overdue_milestone_count,
        "overdue_amount": float(row.overdue_amount or 0),
        "risk_level": row.risk_level,
    }
