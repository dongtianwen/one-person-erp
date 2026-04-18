"""v2.0/v2.2 AI Agent 闭环——规则引擎 + 风险评分 + 策略库。

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


# ────────────────────────────────────────────────────────────
# v2.2 策略库：4 档处置策略模板
# ────────────────────────────────────────────────────────────

ACTION_STRATEGY_LIBRARY: Dict[str, Dict[str, Any]] = {
    "light_reminder": {
        "strategy_code": "light_reminder",
        "strategy_name": "轻度催收",
        "action_steps": [
            "发送短信/微信提醒客户付款",
            "确认客户是否已收到发票",
            "3 个工作日内确认付款时间",
        ],
        "owner": "财务",
        "deadline": "3 个工作日内",
    },
    "escalated_reminder": {
        "strategy_code": "escalated_reminder",
        "strategy_name": "升级催收",
        "action_steps": [
            "财务牵头发送书面催收函",
            "联系客户对接人确认延期原因",
            "48 小时内确认新付款节点",
        ],
        "owner": "财务",
        "deadline": "48 小时内",
    },
    "management_escalation": {
        "strategy_code": "management_escalation",
        "strategy_name": "高层介入",
        "action_steps": [
            "高管直接联系客户决策人",
            "发送正式催款通知并抄送法务",
            "评估是否暂停后续交付",
            "7 天内确认最终解决方案",
        ],
        "owner": "高管",
        "deadline": "7 天内",
    },
    "delivery_suspension": {
        "strategy_code": "delivery_suspension",
        "strategy_name": "暂停交付评估",
        "action_steps": [
            "立即暂停该项目所有后续交付",
            "法务评估合同违约条款",
            "评估是否需要启动诉讼/仲裁",
            "48 小时内出具处置报告",
        ],
        "owner": "高管",
        "deadline": "48 小时内",
    },
}


def _derive_priority(risk_score: int) -> str:
    """从 risk_score 推导 priority：0-25→low, 26-50→medium, 51-100→high。"""
    if risk_score >= 51:
        return "high"
    elif risk_score >= 26:
        return "medium"
    else:
        return "low"


def _match_strategy(risk_score: int, suggestion_type: str = "", data: Optional[dict] = None) -> Dict[str, Any]:
    """按分数和场景匹配策略模板。"""
    if risk_score >= 76:
        return dict(ACTION_STRATEGY_LIBRARY["delivery_suspension"])
    elif risk_score >= 51:
        return dict(ACTION_STRATEGY_LIBRARY["management_escalation"])
    elif risk_score >= 26:
        return dict(ACTION_STRATEGY_LIBRARY["escalated_reminder"])
    else:
        return dict(ACTION_STRATEGY_LIBRARY["light_reminder"])


# ────────────────────────────────────────────────────────────
# v2.2 风险评分引擎
# ────────────────────────────────────────────────────────────


def _calculate_overdue_risk_score(
    max_days_overdue: int,
    total_overdue_amount: float,
    contract_amount: float = 0,
    customer_risk_level: str = "normal",
    acceptance_pending: bool = False,
    invoice_unsigned: bool = False,
) -> Dict[str, int]:
    """计算逾期回款的综合风险评分（0-100）。

    评分维度：
    - days_overdue_score (0-25): 最大逾期天数归一化
    - amount_score (0-20): 逾期金额量级
    - amount_ratio_score (0-20): 逾期金额占合同比
    - customer_risk_score (0-15): 客户历史风险等级
    - acceptance_status_score (0-10): 验收状态
    - invoice_status_score (0-10): 发票状态
    - total_score: 总和，上限 100
    """
    # 1. 逾期天数评分 (0-25)
    if max_days_overdue >= 90:
        days_score = 25
    elif max_days_overdue >= 60:
        days_score = 20
    elif max_days_overdue >= 30:
        days_score = 15
    elif max_days_overdue >= 14:
        days_score = 10
    elif max_days_overdue >= 7:
        days_score = 5
    else:
        days_score = max(1, int(max_days_overdue * 2))

    # 2. 金额评分 (0-20)
    if total_overdue_amount >= 1_000_000:
        amount_score = 20
    elif total_overdue_amount >= 500_000:
        amount_score = 15
    elif total_overdue_amount >= 200_000:
        amount_score = 10
    elif total_overdue_amount >= 100_000:
        amount_score = 5
    else:
        amount_score = max(1, int(total_overdue_amount / 10_000))

    # 3. 金额占比评分 (0-20)
    if contract_amount > 0:
        ratio = total_overdue_amount / contract_amount
        if ratio >= 0.5:
            ratio_score = 20
        elif ratio >= 0.3:
            ratio_score = 15
        elif ratio >= 0.2:
            ratio_score = 10
        elif ratio >= 0.1:
            ratio_score = 5
        else:
            ratio_score = max(1, int(ratio * 50))
    else:
        ratio_score = 10  # 无合同金额时给中等分

    # 4. 客户风险等级评分 (0-15)
    customer_score_map = {"normal": 0, "elevated": 8, "high": 15}
    customer_risk_score = customer_score_map.get(customer_risk_level, 0)

    # 5. 验收状态评分 (0-10)
    acceptance_score = 10 if acceptance_pending else 0

    # 6. 发票状态评分 (0-10)
    invoice_score = 10 if invoice_unsigned else 0

    total = days_score + amount_score + ratio_score + customer_risk_score + acceptance_score + invoice_score
    total = min(total, 100)

    return {
        "total_score": total,
        "days_overdue_score": days_score,
        "amount_score": amount_score,
        "amount_ratio_score": ratio_score,
        "customer_risk_score": customer_risk_score,
        "acceptance_status_score": acceptance_score,
        "invoice_status_score": invoice_score,
    }


def _calculate_profit_risk_score(
    margin_percent: float,
    drop_threshold: float = None,
) -> Dict[str, int]:
    """计算利润率异常的风险评分（0-100）。

    margin_percent 为负数表示亏损。
    """
    if drop_threshold is None:
        drop_threshold = RULE_PROFIT_ANOMALY_DROP_THRESHOLD

    abs_margin = abs(margin_percent)
    if abs_margin >= 50:
        base_score = 60
    elif abs_margin >= 30:
        base_score = 40
    elif abs_margin >= 10:
        base_score = 20
    else:
        base_score = 10

    if margin_percent < 0:
        base_score = min(base_score + 20, 100)

    total = min(base_score, 100)
    return {
        "total_score": total,
        "margin_severity_score": total,
        "negative_margin_bonus": 20 if margin_percent < 0 else 0,
    }


def _calculate_cashflow_risk_score(
    total_cashflow: float,
    weeks_horizon: int,
    urgent_threshold: float = None,
) -> Dict[str, int]:
    """计算现金流风险评分（0-100）。"""
    if urgent_threshold is None:
        urgent_threshold = -500_000

    abs_flow = abs(total_cashflow)
    if total_cashflow >= 0:
        return {"total_score": 0, "magnitude_score": 0, "time_score": 0}

    # 金额评分 (0-50)
    if abs_flow >= 1_000_000:
        magnitude_score = 50
    elif abs_flow >= 500_000:
        magnitude_score = 40
    elif abs_flow >= 200_000:
        magnitude_score = 30
    elif abs_flow >= 100_000:
        magnitude_score = 20
    else:
        magnitude_score = 10

    # 时间评分 (0-30)：周期越短，风险越高
    if weeks_horizon <= 2:
        time_score = 30
    elif weeks_horizon <= 4:
        time_score = 20
    else:
        time_score = 10

    # 紧迫性加分 (0-20)
    if total_cashflow < urgent_threshold:
        urgency_bonus = 20
    else:
        urgency_bonus = 10

    total = min(magnitude_score + time_score + urgency_bonus, 100)
    return {
        "total_score": total,
        "magnitude_score": magnitude_score,
        "time_score": time_score,
        "urgency_bonus": urgency_bonus,
    }


# ────────────────────────────────────────────────────────────
# 建议构建（v2.2 升级：增加 risk_score, strategy_code, score_breakdown, data）
# ────────────────────────────────────────────────────────────


def _build_suggestion(
    decision_type: str,
    suggestion_type: str,
    title: str,
    description: str,
    priority: str = None,
    suggested_action: str = "create_todo",
    source_rule: str = "",
    action_params: Optional[dict] = None,
    risk_score: int = 0,
    score_breakdown: Optional[dict] = None,
    strategy: Optional[dict] = None,
    data: Optional[dict] = None,
) -> Dict[str, Any]:
    """构建结构化建议字典（v2.2 升级）。"""
    import json

    derived_priority = _derive_priority(risk_score)
    final_priority = priority or derived_priority

    return {
        "decision_type": decision_type,
        "suggestion_type": suggestion_type,
        "title": title,
        "description": description,
        "priority": final_priority,
        "status": "pending",
        "suggested_action": suggested_action,
        "action_params": json.dumps(action_params) if action_params else None,
        "source_rule": source_rule,
        "llm_enhanced": 0,
        "risk_score": risk_score,
        "strategy_code": strategy.get("strategy_code", "") if strategy else "",
        "score_breakdown": json.dumps(score_breakdown) if score_breakdown else None,
        "data": json.dumps(data) if data else None,
        "_strategy": strategy,
    }


# ────────────────────────────────────────────────────────────
# 规则引擎（v2.2 升级：附加评分 + 策略 + 业务明细）
# ────────────────────────────────────────────────────────────


async def evaluate_overdue_payments(db: AsyncSession) -> List[Dict[str, Any]]:
    """评估逾期回款。

    检测 payment_due_date < 今日 且 payment_status != received 的里程碑。
    v2.2 升级：附加 risk_score、score_breakdown、strategy、data。
    """
    from app.models.project import Milestone, Project
    from app.models.customer import Customer
    from app.models.acceptance import Acceptance
    from app.models.invoice import Invoice
    from sqlalchemy.orm import joinedload
    today = date.today().isoformat()
    result = await db.execute(
        select(Milestone)
        .options(joinedload(Milestone.project).joinedload(Project.customer))
        .where(
            Milestone.payment_due_date.isnot(None),
            Milestone.payment_due_date < today,
            Milestone.payment_status != "received",
            Milestone.is_deleted == False,
        )
    )
    milestones = result.unique().scalars().all()
    if not milestones:
        return []

    today_date = date.today()
    count = len(milestones)
    total_amount = sum(
        float(m.payment_amount or 0) for m in milestones
    )

    max_days_overdue = 0
    for m in milestones:
        if m.payment_due_date:
            days = (today_date - m.payment_due_date).days
            if days > max_days_overdue:
                max_days_overdue = days

    # 提取具体的逾期明细供 AI 分析
    details = [
        {
            "project_name": m.project.name if m.project else "未知项目",
            "customer_name": m.project.customer.name if m.project and m.project.customer else "",
            "title": m.title,
            "amount": float(m.payment_amount or 0),
            "days_overdue": (today_date - m.payment_due_date).days if m.payment_due_date else 0,
        }
        for m in milestones
    ]

    # 根据逾期情况动态计算客户风险等级
    if max_days_overdue >= 60:
        dynamic_risk = "high"
    elif max_days_overdue >= 14:
        dynamic_risk = "elevated"
    else:
        dynamic_risk = "medium"

    # 将动态风险等级注入到每条明细中
    for d in details:
        d["customer_risk_level"] = dynamic_risk

    # v2.2 评分
    first_m = milestones[0]
    project = first_m.project if first_m.project else None
    customer = project.customer if project else None

    contract_amount = float(getattr(project, "budget", 0) or 0)
    customer_risk = dynamic_risk

    # 验收状态检查
    acceptance_pending = False
    if project:
        try:
            acc_result = await db.execute(
                select(func.count(Acceptance.id)).where(
                    Acceptance.project_id == project.id,
                    Acceptance.is_deleted == False,
                )
            )
            acceptance_pending = (acc_result.scalar() or 0) == 0
        except Exception:
            pass

    # 发票状态检查
    invoice_unsigned = False
    if project:
        try:
            inv_result = await db.execute(
                select(func.count(Invoice.id)).where(
                    Invoice.project_id == project.id,
                    Invoice.status == "issued",
                    Invoice.is_deleted == False,
                )
            )
            invoice_unsigned = (inv_result.scalar() or 0) > 0
        except Exception:
            pass

    score_result = _calculate_overdue_risk_score(
        max_days_overdue=max_days_overdue,
        total_overdue_amount=total_amount,
        contract_amount=contract_amount,
        customer_risk_level=customer_risk,
        acceptance_pending=acceptance_pending,
        invoice_unsigned=invoice_unsigned,
    )

    strategy = _match_strategy(score_result["total_score"], SUGGESTION_TYPE_OVERDUE_PAYMENT)

    return [_build_suggestion(
        decision_type="overdue_payment",
        suggestion_type=SUGGESTION_TYPE_OVERDUE_PAYMENT,
        title=f"发现 {count} 笔逾期回款，风险评分 {score_result['total_score']} 分",
        description=f"共 {count} 笔回款逾期，合计 ¥{total_amount:,.2f}。"
                    f"最大逾期 {max_days_overdue} 天，风险等级 {customer_risk}。",
        suggested_action="create_todo",
        source_rule="overdue_payment_check",
        risk_score=score_result["total_score"],
        score_breakdown=score_result,
        strategy=strategy,
        action_params={
            "action": "跟进逾期回款",
            "count": count,
            "amount": total_amount,
            "details": details,
            "risk_score": score_result["total_score"],
            "strategy": strategy,
        },
        data={
            "milestone_count": count,
            "total_amount": total_amount,
            "max_days_overdue": max_days_overdue,
            "contract_amount": contract_amount,
            "amount_ratio": round(total_amount / contract_amount, 2) if contract_amount > 0 else 0,
            "customer_risk_level": customer_risk,
            "acceptance_pending": acceptance_pending,
            "invoice_unsigned": invoice_unsigned,
            "details": details,
        },
    )]


async def evaluate_profit_anomaly(db: AsyncSession) -> List[Dict[str, Any]]:
    """评估利润异常。

    检测 gross_margin 下降超过阈值的项。
    v2.2 升级：附加 risk_score、score_breakdown、strategy、data。
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
        score_result = _calculate_profit_risk_score(margin)
        strategy = _match_strategy(score_result["total_score"], SUGGESTION_TYPE_PROFIT_ANOMALY)

        items.append(_build_suggestion(
            decision_type="profit_anomaly",
            suggestion_type=SUGGESTION_TYPE_PROFIT_ANOMALY,
            title=f"项目「{p.name}」利润率异常（{margin:.1f}%），风险评分 {score_result['total_score']} 分",
            description=f"项目「{p.name}」当前利润率 {margin:.1f}%，低于正常水平。",
            suggested_action="create_todo",
            source_rule="profit_anomaly_check",
            risk_score=score_result["total_score"],
            score_breakdown=score_result,
            strategy=strategy,
            action_params={
                "project_id": p.id,
                "project_name": p.name,
                "margin": margin,
                "risk_score": score_result["total_score"],
                "strategy": strategy,
            },
            data={
                "project_name": p.name,
                "margin_percent": margin,
                "budget": float(p.budget or 0),
            },
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
    v2.2 升级：附加 risk_score、score_breakdown、strategy、data。
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

        score_result = _calculate_cashflow_risk_score(
            total_cashflow=float(total),
            weeks_horizon=RULE_CASHFLOW_WARNING_WEEKS,
        )
        strategy = _match_strategy(score_result["total_score"], SUGGESTION_TYPE_CASHFLOW_WARNING)

        return [_build_suggestion(
            decision_type="cashflow_warning",
            suggestion_type=SUGGESTION_TYPE_CASHFLOW_WARNING,
            title=f"现金流预警（风险评分 {score_result['total_score']} 分）",
            description=f"未来 {RULE_CASHFLOW_WARNING_WEEKS} 周现金流为负（¥{float(total):,.2f}）。",
            suggested_action="create_reminder",
            source_rule="cashflow_check",
            risk_score=score_result["total_score"],
            score_breakdown=score_result,
            strategy=strategy,
            action_params={
                "weeks": RULE_CASHFLOW_WARNING_WEEKS,
                "amount": float(total),
                "risk_score": score_result["total_score"],
                "strategy": strategy,
            },
            data={
                "total_cashflow": float(total),
                "weeks_horizon": RULE_CASHFLOW_WARNING_WEEKS,
                "urgent_total": float(urgent_total),
            },
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
    """运行经营决策规则（组合 + 排序）。

    v2.2 升级：规则引擎现在自动计算风险评分和匹配策略。
    """
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
        risk_tag = f"[风险: {r.get('risk_score', 'N/A')}] "
        lines.append(f"{priority_tag} {risk_tag}{r['title']}\n  {r['description']}")
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
