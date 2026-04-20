"""v2.2 summary 底座服务——仪表盘聚合层。

核心函数：
- refresh_summary: 触发事件驱动的局部刷新
- rebuild_summary_full: 全量重建
"""

import json
import logging
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dashboard_summary import DashboardSummary
from app.core.constants import (
    SUMMARY_TRIGGER_WHITELIST,
    SUMMARY_TRIGGER_METRIC_MAP,
    DASHBOARD_METRIC_KEY_WHITELIST,
    WARNING_SUMMARY_REFRESH_FAILED,
)

logger = logging.getLogger(__name__)


async def refresh_summary(
    db: AsyncSession,
    trigger_event: str,
    related_ids: dict[str, Any] | None = None,
) -> tuple[bool, str | None]:
    """触发 summary 局部刷新。

    trigger_event 必须是 SUMMARY_TRIGGER_* 常量之一，否则不执行刷新。
    返回 (True, None) 表示成功（或无需刷新）；
    返回 (False, warning_code) 表示失败。
    """
    if trigger_event not in SUMMARY_TRIGGER_WHITELIST:
        return True, None

    affected_keys = SUMMARY_TRIGGER_METRIC_MAP.get(trigger_event, [])
    if not affected_keys:
        return True, None

    try:
        for metric_key in affected_keys:
            value = await _compute_metric(db, metric_key)
            await _upsert_metric(db, metric_key, value)
        await db.commit()
        return True, None
    except Exception as e:
        logger.error(
            "summary 刷新失败 | trigger_event=%s error=%s",
            trigger_event, e,
        )
        await db.rollback()
        return False, WARNING_SUMMARY_REFRESH_FAILED


async def rebuild_summary_full(db: AsyncSession) -> bool:
    """全量重建 dashboard_summary。"""
    try:
        for metric_key in DASHBOARD_METRIC_KEY_WHITELIST:
            value = await _compute_metric(db, metric_key)
            await _upsert_metric(db, metric_key, value)
        await db.commit()
        return True
    except Exception as e:
        logger.error("summary 全量重建失败 | error=%s", e)
        await db.rollback()
        return False


async def _upsert_metric(db: AsyncSession, metric_key: str, value: Any) -> None:
    """INSERT ON CONFLICT UPDATE 单行 metric。"""
    result = await db.execute(
        select(DashboardSummary).where(DashboardSummary.metric_key == metric_key)
    )
    row = result.scalar_one_or_none()
    if row is None:
        row = DashboardSummary(
            metric_key=metric_key,
            metric_value=json.dumps(value, ensure_ascii=False) if value is not None else None,
        )
        db.add(row)
    else:
        row.metric_value = json.dumps(value, ensure_ascii=False) if value is not None else None


async def _compute_metric(db: AsyncSession, metric_key: str) -> Any:
    """从源表计算单个 metric 值。"""
    from app.models.customer import Customer
    from app.models.project import Project, Milestone
    from app.models.contract import Contract
    from app.models.finance import FinanceRecord
    from app.models.agent_suggestion import AgentSuggestion
    from app.core.constants import (
        METRIC_CLIENT_COUNT,
        METRIC_CLIENT_RISK_HIGH_COUNT,
        METRIC_PROJECT_ACTIVE_COUNT,
        METRIC_PROJECT_AT_RISK_COUNT,
        METRIC_CONTRACT_ACTIVE_COUNT,
        METRIC_CONTRACT_TOTAL_AMOUNT,
        METRIC_FINANCE_RECEIVABLE_TOTAL,
        METRIC_FINANCE_OVERDUE_TOTAL,
        METRIC_FINANCE_OVERDUE_COUNT,
        METRIC_DELIVERY_IN_PROGRESS_COUNT,
        METRIC_DELIVERY_COMPLETED_THIS_MONTH,
        METRIC_AGENT_PENDING_COUNT,
        METRIC_AGENT_HIGH_PRIORITY_COUNT,
    )

    try:
        if metric_key == METRIC_CLIENT_COUNT:
            result = await db.execute(select(func.count(Customer.id)))
            return result.scalar() or 0

        if metric_key == METRIC_CLIENT_RISK_HIGH_COUNT:
            result = await db.execute(
                select(func.count(Customer.id)).where(Customer.risk_level == "high")
            )
            return result.scalar() or 0

        if metric_key == METRIC_PROJECT_ACTIVE_COUNT:
            result = await db.execute(
                select(func.count(Project.id)).where(
                    Project.status.notin_(["completed", "paused", "delivery"]),
                    Project.is_deleted == False,
                )
            )
            return result.scalar() or 0

        if metric_key == METRIC_PROJECT_AT_RISK_COUNT:
            result = await db.execute(
                select(func.count(Project.id)).where(
                    Project.status.notin_(["completed", "paused", "delivery"]),
                    Project.is_deleted == False,
                )
            )
            return result.scalar() or 0

        if metric_key == METRIC_CONTRACT_ACTIVE_COUNT:
            result = await db.execute(
                select(func.count(Contract.id)).where(
                    Contract.status.in_(["active", "executing"]),
                    Contract.is_deleted == False,
                )
            )
            return result.scalar() or 0

        if metric_key == METRIC_CONTRACT_TOTAL_AMOUNT:
            result = await db.execute(
                select(func.coalesce(func.sum(Contract.amount), 0)).where(
                    Contract.status.in_(["active", "executing"]),
                    Contract.is_deleted == False,
                )
            )
            return float(result.scalar() or 0)

        if metric_key == METRIC_FINANCE_RECEIVABLE_TOTAL:
            contract_total = await db.execute(
                select(func.coalesce(func.sum(Contract.amount), 0)).where(
                    Contract.status.in_(["active", "executing"]),
                    Contract.is_deleted == False,
                )
            )
            paid_total = await db.execute(
                select(func.coalesce(func.sum(FinanceRecord.amount), 0)).where(
                    FinanceRecord.type == "income",
                    FinanceRecord.status.in_(["paid", "confirmed"]),
                    FinanceRecord.is_deleted == False,
                )
            )
            ct = float(contract_total.scalar() or 0)
            pt = float(paid_total.scalar() or 0)
            return max(0.0, round(ct - pt, 2))

        if metric_key == METRIC_FINANCE_OVERDUE_TOTAL:
            from datetime import datetime
            result = await db.execute(
                select(func.coalesce(func.sum(Milestone.payment_amount), 0)).where(
                    Milestone.payment_status == "pending",
                    Milestone.payment_due_date < datetime.utcnow(),
                )
            )
            return float(result.scalar() or 0)

        if metric_key == METRIC_FINANCE_OVERDUE_COUNT:
            from datetime import datetime
            result = await db.execute(
                select(func.count(Milestone.id)).where(
                    Milestone.payment_status == "pending",
                    Milestone.payment_due_date < datetime.utcnow(),
                )
            )
            return result.scalar() or 0

        if metric_key == METRIC_DELIVERY_IN_PROGRESS_COUNT:
            result = await db.execute(
                select(func.count(Project.id)).where(Project.status == "in_progress")
            )
            return result.scalar() or 0

        if metric_key == METRIC_DELIVERY_COMPLETED_THIS_MONTH:
            from datetime import datetime
            now = datetime.utcnow()
            result = await db.execute(
                select(func.count(Project.id)).where(
                    Project.status == "completed",
                    func.strftime("%Y-%m", Project.updated_at) == now.strftime("%Y-%m"),
                )
            )
            return result.scalar() or 0

        if metric_key == METRIC_AGENT_PENDING_COUNT:
            result = await db.execute(
                select(func.count(AgentSuggestion.id)).where(
                    AgentSuggestion.status == "pending"
                )
            )
            return result.scalar() or 0

        if metric_key == METRIC_AGENT_HIGH_PRIORITY_COUNT:
            result = await db.execute(
                select(func.count(AgentSuggestion.id)).where(
                    AgentSuggestion.status == "pending",
                    AgentSuggestion.priority == "high",
                )
            )
            return result.scalar() or 0

    except Exception as e:
        logger.warning("metric 计算失败 | metric_key=%s error=%s", metric_key, e)
        return None

    return None
