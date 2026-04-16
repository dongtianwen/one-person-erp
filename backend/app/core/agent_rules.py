"""v2.0 AI Agent 闭环——规则引擎。

所有决策逻辑基于常量阈值，LLM 仅做语言增强。
"""
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    RULE_OVERDUE_PAYMENT_WARN_DAYS,
    RULE_CUSTOMER_OVERDUE_WARN_THRESHOLD,
    RULE_CUSTOMER_OVERDUE_HIGH_THRESHOLD,
    RULE_CUSTOMER_OVERDUE_HIGH_RATIO,
    RULE_PROFIT_ANOMALY_DROP_THRESHOLD,
    RULE_MILESTONE_RISK_DAYS,
    RULE_TASK_DELAY_DAYS,
    RULE_CASHFLOW_URGENT_WEEKS,
    RULE_CASHFLOW_WARNING_WEEKS,
    SUGGESTION_TYPE_OVERDUE_PAYMENT,
    SUGGESTION_TYPE_PROFIT_ANOMALY,
    SUGGESTION_TYPE_MILESTONE_RISK,
    SUGGESTION_TYPE_CASHFLOW_WARNING,
    SUGGESTION_TYPE_TASK_DELAY,
    SUGGESTION_TYPE_CHANGE_IMPACT,
    SUGGESTION_TYPE_DELIVERY_MISSING_MODEL,
    SUGGESTION_TYPE_DELIVERY_MISSING_DATASET,
    SUGGESTION_TYPE_DELIVERY_MISSING_ACCEPTANCE,
    SUGGESTION_TYPE_DELIVERY_VERSION_MISMATCH,
    SUGGESTION_TYPE_DELIVERY_EMPTY_PACKAGE,
    SUGGESTION_TYPE_DELIVERY_UNBOUND_PROJECT,
    PRIORITY_WHITELIST,
)

logger = logging.getLogger(__name__)


def _build_suggestion(
    decision_type: str,
    suggestion_type: str,
    title: str,
    description: str,
    priority: str,
    suggested_action: str = "create_todo",
    source_rule: str = "",
    action_params: Optional[dict] = None,
) -> Dict[str, Any]:
    """构建结构化建议字典。"""
    import json
    return {
        "decision_type": decision_type,
        "suggestion_type": suggestion_type,
        "title": title,
        "description": description,
        "priority": priority,
        "status": "pending",
        "suggested_action": suggested_action,
        "action_params": json.dumps(action_params) if action_params else None,
        "source_rule": source_rule,
        "llm_enhanced": 0,
    }


async def evaluate_overdue_payments(db: AsyncSession) -> List[Dict[str, Any]]:
    """评估逾期回款。

    检测 payment_due_date < 今日 且 payment_status != received 的里程碑。
    """
    from app.models.project import Milestone
    from sqlalchemy.orm import selectinload
    today = date.today().isoformat()
    result = await db.execute(
        select(Milestone).options(selectinload(Milestone.project)).where(
            Milestone.payment_due_date.isnot(None),
            Milestone.payment_due_date < today,
            Milestone.payment_status != "received",
            Milestone.is_deleted == False,
        )
    )
    milestones = result.scalars().all()
    if not milestones:
        return []

    today_date = date.today()
    count = len(milestones)
    total_amount = sum(
        float(m.payment_amount or 0) for m in milestones
    )
    priority = "high" if count >= RULE_CUSTOMER_OVERDUE_HIGH_THRESHOLD else "medium"

    # 提取具体的逾期明细供 AI 分析
    details = [
        {
            "project_name": m.project.name if m.project else "未知项目",
            "title": m.title,
            "amount": float(m.payment_amount or 0),
            "days_overdue": (today_date - m.payment_due_date).days if m.payment_due_date else 0
        }
        for m in milestones
    ]

    return [_build_suggestion(
        decision_type="overdue_payment",
        suggestion_type=SUGGESTION_TYPE_OVERDUE_PAYMENT,
        title=f"发现 {count} 笔逾期回款",
        description=f"共 {count} 笔回款逾期，合计 ¥{total_amount:,.2f}，建议尽快跟进。",
        priority=priority,
        suggested_action="create_todo",
        source_rule="overdue_payment_check",
        action_params={"action": "跟进逾期回款", "count": count, "amount": total_amount, "details": details},
    )]


async def evaluate_profit_anomaly(db: AsyncSession) -> List[Dict[str, Any]]:
    """评估利润异常。

    检测 gross_margin 下降超过阈值的项。
    """
    from app.models.project import Project
    result = await db.execute(
        select(Project).where(
            Project.cached_gross_margin.isnot(None),
            Project.cached_gross_margin < -RULE_PROFIT_ANOMALY_DROP_THRESHOLD,
            Project.is_deleted == False,
        )
    )
    projects = result.scalars().all()
    if not projects:
        return []

    items = []
    for p in projects:
        margin = float(p.cached_gross_margin) * 100
        items.append(_build_suggestion(
            decision_type="profit_anomaly",
            suggestion_type=SUGGESTION_TYPE_PROFIT_ANOMALY,
            title=f"项目「{p.name}」利润率异常",
            description=f"项目「{p.name}」当前利润率 {margin:.1f}%，低于正常水平。",
            priority="high",
            suggested_action="create_todo",
            source_rule="profit_anomaly_check",
            action_params={"project_id": p.id, "project_name": p.name, "margin": margin},
        ))
    return items


async def evaluate_milestone_risk(db: AsyncSession, project_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """评估里程碑风险。

    检测距到期日 <= RULE_MILESTONE_RISK_DAYS 天且未完成的里程碑。
    """
    from app.models.project import Milestone
    from sqlalchemy import text
    today = date.today().isoformat()
    risk_date = (date.today() + __import__("datetime").timedelta(days=RULE_MILESTONE_RISK_DAYS)).isoformat()

    query = select(Milestone).where(
        Milestone.is_completed == False,
        Milestone.due_date.isnot(None),
        Milestone.due_date <= risk_date,
        Milestone.is_deleted == False,
    )
    if project_id:
        query = query.where(Milestone.project_id == project_id)

    result = await db.execute(query)
    milestones = result.scalars().all()
    if not milestones:
        return []

    items = []
    for m in milestones:
        days_left = (m.due_date - date.today()).days if m.due_date else 0
        items.append(_build_suggestion(
            decision_type="milestone_risk",
            suggestion_type=SUGGESTION_TYPE_MILESTONE_RISK,
            title=f"里程碑「{m.title}」存在延期风险",
            description=f"里程碑「{m.title}」还有 {days_left} 天到期，建议加快进度。",
            priority="high" if days_left <= 3 else "medium",
            suggested_action="create_todo",
            source_rule="milestone_risk_check",
            action_params={"milestone_id": m.id, "milestone_title": m.title, "days_left": days_left},
        ))
    return items


async def evaluate_cashflow_warning(db: AsyncSession) -> List[Dict[str, Any]]:
    """评估现金流预警。

    表不存在时返回空列表。
    """
    try:
        from app.models.finance import FinanceRecord
        from datetime import timedelta
        today = date.today()
        warning_date = today + timedelta(weeks=RULE_CASHFLOW_WARNING_WEEKS)

        result = await db.execute(
            select(func.sum(FinanceRecord.amount)).where(
                FinanceRecord.date <= warning_date,
                FinanceRecord.is_deleted == False,
            )
        )
        total = result.scalar() or 0
        if total >= 0:
            return []

        urgent_date = today + timedelta(weeks=RULE_CASHFLOW_URGENT_WEEKS)
        result_urgent = await db.execute(
            select(func.sum(FinanceRecord.amount)).where(
                FinanceRecord.date <= urgent_date,
                FinanceRecord.is_deleted == False,
            )
        )
        urgent_total = result_urgent.scalar() or 0

        priority = "high" if urgent_total < 0 else "medium"
        return [_build_suggestion(
            decision_type="cashflow_warning",
            suggestion_type=SUGGESTION_TYPE_CASHFLOW_WARNING,
            title="现金流预警",
            description=f"未来 {RULE_CASHFLOW_WARNING_WEEKS} 周现金流为负（¥{float(total):,.2f}）。",
            priority=priority,
            suggested_action="create_reminder",
            source_rule="cashflow_check",
            action_params={"weeks": RULE_CASHFLOW_WARNING_WEEKS, "amount": float(total)},
        )]
    except Exception as e:
        logger.warning("现金流预警规则执行失败（可能表不存在）: %s", e)
        return []


async def evaluate_task_delay(db: AsyncSession, project_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """评估任务延期。

    检测 due_date < 今日 且 status != completed 的任务。
    """
    from app.models.project import Task
    today = date.today().isoformat()

    query = select(Task).where(
        Task.due_date.isnot(None),
        Task.due_date < today,
        Task.status != "completed",
        Task.is_deleted == False,
    )
    if project_id:
        query = query.where(Task.project_id == project_id)

    result = await db.execute(query)
    tasks = result.scalars().all()
    if not tasks:
        return []

    items = []
    for t in tasks:
        days_overdue = (date.today() - t.due_date).days if t.due_date else 0
        items.append(_build_suggestion(
            decision_type="task_delay",
            suggestion_type=SUGGESTION_TYPE_TASK_DELAY,
            title=f"任务「{t.title}」已延期",
            description=f"任务「{t.title}」已延期 {days_overdue} 天。",
            priority="medium",
            suggested_action="create_reminder",
            source_rule="task_delay_check",
            action_params={"task_id": t.id, "task_title": t.title, "days_overdue": days_overdue},
        ))
    return items


async def evaluate_change_impact(db: AsyncSession) -> List[Dict[str, Any]]:
    """评估变更影响。

    检测近期未确认的变更单。
    """
    from app.models.change_order import ChangeOrder
    from app.models.contract import Contract
    from sqlalchemy.orm import selectinload
    from datetime import timedelta
    cutoff = (date.today() - timedelta(days=30)).isoformat()
    result = await db.execute(
        select(ChangeOrder).options(
            selectinload(ChangeOrder.contract).selectinload(Contract.project)
        ).where(
            ChangeOrder.status == "pending",
            ChangeOrder.created_at >= cutoff,
            ChangeOrder.is_deleted == False,
        )
    )
    changes = result.scalars().all()
    if not changes:
        return []

    # 提取变更单明细给 AI 提供更充实的上下文
    details = [
        {
            "project_name": (c.contract.project.name if c.contract and c.contract.project else c.contract.title if c.contract else "未知项目"),
            "title": c.title,
            "amount": float(c.amount or 0),
            "days_pending": (date.today() - c.created_at.date()).days if c.created_at else 0
        }
        for c in changes
    ]

    return [_build_suggestion(
        decision_type="change_impact",
        suggestion_type=SUGGESTION_TYPE_CHANGE_IMPACT,
        title=f"有 {len(changes)} 条待确认的变更单",
        description=f"近 30 天内有 {len(changes)} 条变更单待确认，请及时处理。",
        priority="medium",
        suggested_action="none",
        source_rule="change_impact_check",
        action_params={"change_count": len(changes), "details": details},
    )]


def _priority_sort_key(suggestion: Dict[str, Any]) -> int:
    """按优先级排序：high=0, medium=1, low=2。"""
    order = {"high": 0, "medium": 1, "low": 2}
    return order.get(suggestion.get("priority", "medium"), 1)


async def run_business_decision_rules(db: AsyncSession) -> List[Dict[str, Any]]:
    """运行经营决策规则（组合 + 排序）。"""
    all_suggestions: List[Dict[str, Any]] = []
    for evaluator in [
        evaluate_overdue_payments,
        evaluate_profit_anomaly,
        evaluate_cashflow_warning,
    ]:
        try:
            results = await evaluator(db)
            all_suggestions.extend(results)
        except Exception as e:
            logger.error("规则引擎执行失败: %s | rule=%s", e, evaluator.__name__)
    all_suggestions.sort(key=_priority_sort_key)
    return all_suggestions


async def run_project_management_rules(db: AsyncSession, project_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """运行项目管理规则（组合）。"""
    all_suggestions: List[Dict[str, Any]] = []
    for evaluator in [
        lambda db: evaluate_milestone_risk(db, project_id),
        lambda db: evaluate_task_delay(db, project_id),
        evaluate_change_impact,
    ]:
        try:
            results = await evaluator(db)
            all_suggestions.extend(results)
        except Exception as e:
            logger.error("规则引擎执行失败: %s | rule=%s", e, evaluator.__name__)
    all_suggestions.sort(key=_priority_sort_key)
    return all_suggestions


def build_rule_plain_text(rules: List[Dict[str, Any]]) -> str:
    """将规则引擎输出格式化为纯文本。"""
    if not rules:
        return "未检测到异常。"
    lines = []
    for r in rules:
        priority_tag = f"[{r['priority'].upper()}]"
        lines.append(f"{priority_tag} {r['title']}\n  {r['description']}")
    return "\n".join(lines)


async def evaluate_delivery_package(db: AsyncSession, package_id: int) -> List[Dict[str, Any]]:
    """评估交付包完整性。"""
    from app.models.delivery_package import DeliveryPackage
    from app.core.error_codes import ERROR_CODES
    from app.core.exception_handlers import BusinessException

    result = await db.execute(
        select(DeliveryPackage).where(DeliveryPackage.id == package_id)
    )
    pkg = result.scalar_one_or_none()
    if not pkg:
        raise BusinessException(
            status_code=404,
            detail=ERROR_CODES["DELIVERY_QC_NO_PACKAGE"],
            code="DELIVERY_QC_NO_PACKAGE",
        )

    suggestions: List[Dict[str, Any]] = []

    has_model = await _has_model_version(db, package_id)
    if not has_model:
        suggestions.append(_build_suggestion(
            decision_type="delivery_qc",
            suggestion_type=SUGGESTION_TYPE_DELIVERY_MISSING_MODEL,
            title="交付包缺少模型版本",
            description=f"交付包「{pkg.name}」未关联任何模型版本，请补充。",
            priority="high",
            suggested_action="create_todo",
            source_rule="delivery_missing_model",
        ))

    has_dataset = await _has_dataset_version(db, package_id)
    if not has_dataset:
        suggestions.append(_build_suggestion(
            decision_type="delivery_qc",
            suggestion_type=SUGGESTION_TYPE_DELIVERY_MISSING_DATASET,
            title="交付包缺少数据集版本",
            description=f"交付包「{pkg.name}」未关联任何数据集版本，请补充。",
            priority="medium",
            suggested_action="create_todo",
            source_rule="delivery_missing_dataset",
        ))

    has_acceptance = await _has_acceptance_record(db, package_id, pkg)
    if not has_acceptance:
        suggestions.append(_build_suggestion(
            decision_type="delivery_qc",
            suggestion_type=SUGGESTION_TYPE_DELIVERY_MISSING_ACCEPTANCE,
            title="交付包缺少验收记录",
            description=f"交付包「{pkg.name}」尚未完成验收，请安排验收。",
            priority="high",
            suggested_action="create_reminder",
            source_rule="delivery_missing_acceptance",
        ))

    has_deprecated = await _has_deprecated_model(db, package_id)
    if has_deprecated:
        suggestions.append(_build_suggestion(
            decision_type="delivery_qc",
            suggestion_type=SUGGESTION_TYPE_DELIVERY_VERSION_MISMATCH,
            title="交付包关联了已废弃的模型版本",
            description=f"交付包「{pkg.name}」关联的模型版本已废弃，请更新。",
            priority="high",
            suggested_action="create_todo",
            source_rule="delivery_version_mismatch",
        ))

    is_empty = await _is_empty_package(db, package_id, pkg)
    if is_empty:
        suggestions.append(_build_suggestion(
            decision_type="delivery_qc",
            suggestion_type=SUGGESTION_TYPE_DELIVERY_EMPTY_PACKAGE,
            title="交付包为空",
            description=f"交付包「{pkg.name}」无任何关键内容，请补充交付物。",
            priority="high",
            suggested_action="create_todo",
            source_rule="delivery_empty_package",
        ))

    if not pkg.project_id:
        suggestions.append(_build_suggestion(
            decision_type="delivery_qc",
            suggestion_type=SUGGESTION_TYPE_DELIVERY_UNBOUND_PROJECT,
            title="交付包未绑定项目",
            description=f"交付包「{pkg.name}」未绑定有效项目，请关联项目。",
            priority="high",
            suggested_action="create_todo",
            source_rule="delivery_unbound_project",
        ))

    return suggestions


async def _has_model_version(db: AsyncSession, package_id: int) -> bool:
    try:
        from app.models.delivery_package import PackageModelVersion
        result = await db.execute(
            select(func.count(PackageModelVersion.id)).where(
                PackageModelVersion.package_id == package_id
            )
        )
        return (result.scalar() or 0) > 0
    except Exception:
        return False


async def _has_dataset_version(db: AsyncSession, package_id: int) -> bool:
    try:
        from app.models.delivery_package import PackageDatasetVersion
        result = await db.execute(
            select(func.count(PackageDatasetVersion.id)).where(
                PackageDatasetVersion.package_id == package_id
            )
        )
        return (result.scalar() or 0) > 0
    except Exception:
        return False


async def _has_acceptance_record(db: AsyncSession, package_id: int, pkg) -> bool:
    if getattr(pkg, "status", None) == "accepted":
        return True
    try:
        from app.models.acceptance import Acceptance
        result = await db.execute(
            select(func.count(Acceptance.id)).where(
                Acceptance.delivery_package_id == package_id,
                Acceptance.is_deleted == False,
            )
        )
        return (result.scalar() or 0) > 0
    except Exception:
        return False


async def _has_deprecated_model(db: AsyncSession, package_id: int) -> bool:
    try:
        from app.models.delivery_package import PackageModelVersion
        from app.models.model_version import ModelVersion
        result = await db.execute(
            select(func.count(ModelVersion.id))
            .join(PackageModelVersion, PackageModelVersion.model_version_id == ModelVersion.id)
            .where(
                PackageModelVersion.package_id == package_id,
                ModelVersion.status == "deprecated",
            )
        )
        return (result.scalar() or 0) > 0
    except Exception:
        return False


async def _is_empty_package(db: AsyncSession, package_id: int, pkg) -> bool:
    has_model = await _has_model_version(db, package_id)
    has_dataset = await _has_dataset_version(db, package_id)
    has_desc = bool(getattr(pkg, "description", None))
    return not has_model and not has_dataset and not has_desc


async def run_delivery_qc_rules(db: AsyncSession, package_id: int) -> List[Dict[str, Any]]:
    """运行交付质检规则（组合）。"""
    return await evaluate_delivery_package(db, package_id)
