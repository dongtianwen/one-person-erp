"""v1.4 客户生命周期价值核心函数——可独立于 FastAPI 应用直接调用和测试。"""
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
from datetime import date as date_type

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.contract import Contract
from app.models.finance import FinanceRecord
from app.models.project import Project
from app.core.constants import DECIMAL_PLACES


async def calculate_customer_lifetime_value(customer_id: int, db: AsyncSession) -> dict:
    """
    计算客户生命周期价值。

    返回：
      total_contract_amount: Decimal（历史合同总额，不限合同状态）
      total_received_amount: Decimal（历史实收金额，已确认收入）
      project_count: int（合作项目数，不限项目状态）
      avg_project_amount: Decimal | None（平均项目金额，项目数为 0 时返回 None）
      first_cooperation_date: date | None（最早合同 sign_date，无数据返回 None）
      last_cooperation_date: date | None（最新合同 sign_date，无数据返回 None）
    所有金额 round(x, 2)
    """
    # 历史合同总额（不限合同状态）
    contract_total_result = await db.execute(
        select(func.coalesce(func.sum(Contract.amount), 0)).where(
            Contract.customer_id == customer_id,
            Contract.is_deleted == False,
        )
    )
    total_contract_amount = Decimal(str(round(contract_total_result.scalar(), DECIMAL_PLACES)))

    # 历史实收金额（已确认收入，关联合同属于该客户）
    received_result = await db.execute(
        select(func.coalesce(func.sum(FinanceRecord.amount), 0)).where(
            FinanceRecord.type == "income",
            FinanceRecord.status.in_(["confirmed", "paid"]),
            FinanceRecord.is_deleted == False,
            FinanceRecord.contract_id.in_(
                select(Contract.id).where(
                    Contract.customer_id == customer_id,
                    Contract.is_deleted == False,
                )
            ),
        )
    )
    total_received_amount = Decimal(str(round(received_result.scalar(), DECIMAL_PLACES)))

    # 合作项目数（不限项目状态）
    project_count_result = await db.execute(
        select(func.count(Project.id)).where(
            Project.customer_id == customer_id,
            Project.is_deleted == False,
        )
    )
    project_count = project_count_result.scalar() or 0

    # 平均项目金额
    avg_project_amount: Optional[Decimal] = None
    if project_count > 0:
        avg_project_amount = (total_contract_amount / project_count).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    # 首次合作日期（最早 sign_date，排除 NULL）
    first_date_result = await db.execute(
        select(func.min(Contract.signed_date)).where(
            Contract.customer_id == customer_id,
            Contract.is_deleted == False,
            Contract.signed_date.isnot(None),
        )
    )
    first_cooperation_date = first_date_result.scalar()

    # 最近合作日期（最新 sign_date，排除 NULL）
    last_date_result = await db.execute(
        select(func.max(Contract.signed_date)).where(
            Contract.customer_id == customer_id,
            Contract.is_deleted == False,
            Contract.signed_date.isnot(None),
        )
    )
    last_cooperation_date = last_date_result.scalar()

    return {
        "total_contract_amount": total_contract_amount,
        "total_received_amount": total_received_amount,
        "project_count": project_count,
        "avg_project_amount": avg_project_amount,
        "first_cooperation_date": first_cooperation_date,
        "last_cooperation_date": last_cooperation_date,
    }
