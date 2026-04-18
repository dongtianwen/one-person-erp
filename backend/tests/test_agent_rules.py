"""v2.0/v2.2 规则引擎 + 风险评分测试。"""
import pytest
from datetime import date, timedelta
from decimal import Decimal

from app.core.agent_rules import (
    evaluate_overdue_payments,
    evaluate_profit_anomaly,
    evaluate_milestone_risk,
    evaluate_cashflow_warning,
    evaluate_task_delay,
    evaluate_change_impact,
    run_business_decision_rules,
    run_project_management_rules,
    build_rule_plain_text,
    _build_suggestion,
    _priority_sort_key,
    _derive_priority,
)
from app.models.project import Milestone, Project, Task


@pytest.mark.asyncio
async def test_evaluate_overdue_payments_no_overdue(db_session):
    """无逾期时应返回空列表。"""
    results = await evaluate_overdue_payments(db_session)
    assert results == []


@pytest.mark.asyncio
async def test_evaluate_overdue_payments_detects_overdue(db_session):
    """应检测到逾期回款。"""
    from app.models.customer import Customer
    customer = Customer(name="测试客户", contact_person="张三", email="test@test.com")
    db_session.add(customer)
    await db_session.flush()

    project = Project(name="测试项目", customer_id=customer.id, budget=200000)
    db_session.add(project)
    await db_session.flush()

    milestone = Milestone(
        project_id=project.id,
        title="测试里程碑",
        due_date=date.today() - timedelta(days=10),
        payment_due_date=date.today() - timedelta(days=5),
        payment_amount=Decimal("10000.00"),
        payment_status="unpaid",
        is_completed=False,
    )
    db_session.add(milestone)
    await db_session.commit()

    results = await evaluate_overdue_payments(db_session)
    assert len(results) == 1
    assert results[0]["suggestion_type"] == "overdue_payment"
    assert results[0]["risk_score"] > 0
    assert "score_breakdown" in results[0]
    assert "data" in results[0]


@pytest.mark.asyncio
async def test_evaluate_profit_anomaly_no_anomaly(db_session):
    """利润正常时应返回空列表。"""
    results = await evaluate_profit_anomaly(db_session)
    assert results == []


@pytest.mark.asyncio
async def test_evaluate_profit_anomaly_detects_drop(db_session):
    """应检测到利润率异常下降。"""
    project = Project(
        name="异常项目",
        customer_id=1,
        cached_gross_margin=Decimal("-0.50"),
    )
    db_session.add(project)
    await db_session.commit()

    results = await evaluate_profit_anomaly(db_session)
    assert len(results) == 1
    assert results[0]["suggestion_type"] == "profit_anomaly"
    assert results[0]["risk_score"] >= 51
    assert results[0]["priority"] == "high"


@pytest.mark.asyncio
async def test_evaluate_milestone_risk_no_risk(db_session):
    """无风险里程碑时应返回空列表。"""
    results = await evaluate_milestone_risk(db_session)
    assert results == []


@pytest.mark.asyncio
async def test_evaluate_milestone_risk_detects_risk(db_session):
    """应检测到里程碑风险。"""
    milestone = Milestone(
        project_id=1,
        title="即将到期里程碑",
        due_date=date.today() + timedelta(days=3),
        is_completed=False,
    )
    db_session.add(milestone)
    await db_session.commit()

    results = await evaluate_milestone_risk(db_session)
    assert len(results) == 1
    assert results[0]["suggestion_type"] == "milestone_risk"


@pytest.mark.asyncio
async def test_evaluate_milestone_risk_with_project_id(db_session):
    """支持按项目 ID 过滤。"""
    results = await evaluate_milestone_risk(db_session, project_id=999)
    assert results == []


@pytest.mark.asyncio
async def test_evaluate_cashflow_warning_no_table(db_session):
    """现金流表不存在时应返回空列表（ gracefully degrade）。"""
    results = await evaluate_cashflow_warning(db_session)
    assert isinstance(results, list)


@pytest.mark.asyncio
async def test_evaluate_task_delay_no_delay(db_session):
    """无延期任务时应返回空列表。"""
    results = await evaluate_task_delay(db_session)
    assert results == []


@pytest.mark.asyncio
async def test_evaluate_task_delay_detects_delay(db_session):
    """应检测到延期任务。"""
    task = Task(
        project_id=1,
        title="延期任务",
        due_date=date.today() - timedelta(days=5),
        status="todo",
    )
    db_session.add(task)
    await db_session.commit()

    results = await evaluate_task_delay(db_session)
    assert len(results) == 1
    assert results[0]["suggestion_type"] == "task_delay"


@pytest.mark.asyncio
async def test_evaluate_task_delay_with_project_id(db_session):
    """支持按项目 ID 过滤延期任务。"""
    results = await evaluate_task_delay(db_session, project_id=999)
    assert results == []


@pytest.mark.asyncio
async def test_evaluate_change_impact_no_changes(db_session):
    """无待确认变更单时应返回空列表。"""
    results = await evaluate_change_impact(db_session)
    assert results == []


@pytest.mark.asyncio
async def test_run_business_decision_rules_returns_sorted(db_session):
    """经营决策规则应返回按优先级排序的结果。"""
    results = await run_business_decision_rules(db_session)
    assert isinstance(results, list)
    if len(results) >= 2:
        order = {"high": 0, "medium": 1, "low": 2}
        assert order[results[0]["priority"]] <= order[results[1]["priority"]]


@pytest.mark.asyncio
async def test_run_project_management_rules_returns_sorted(db_session):
    """项目管理规则应返回按优先级排序的结果。"""
    results = await run_project_management_rules(db_session)
    assert isinstance(results, list)


@pytest.mark.asyncio
async def test_run_project_management_rules_with_project_id(db_session):
    """项目管理规则支持按项目 ID 过滤。"""
    results = await run_project_management_rules(db_session, project_id=999)
    assert isinstance(results, list)


def test_build_rule_plain_text_empty():
    """空规则列表应返回默认文本。"""
    assert build_rule_plain_text([]) == "未检测到异常。"


def test_build_rule_plain_text_formats_rules():
    """应正确格式化规则。"""
    rules = [
        {"priority": "high", "title": "标题", "description": "描述"},
    ]
    text = build_rule_plain_text(rules)
    assert "[HIGH]" in text
    assert "标题" in text
    assert "描述" in text


def test_build_suggestion_creates_dict():
    """应创建格式正确的建议字典。"""
    s = _build_suggestion(
        decision_type="test",
        suggestion_type="test_type",
        title="测试",
        description="测试描述",
        priority="high",
    )
    assert s["decision_type"] == "test"
    assert s["status"] == "pending"
    assert s["llm_enhanced"] == 0
    assert s["risk_score"] == 0
    assert s["strategy_code"] == ""


def test_build_suggestion_with_risk_scoring():
    """应正确附加风险评分和策略信息。"""
    s = _build_suggestion(
        decision_type="overdue_payment",
        suggestion_type="overdue_payment",
        title="逾期回款",
        description="描述",
        risk_score=60,
        score_breakdown={"total_score": 60, "days_overdue_score": 15},
        strategy={"strategy_code": "management_escalation", "strategy_name": "高层介入"},
    )
    assert s["risk_score"] == 60
    assert s["strategy_code"] == "management_escalation"
    assert s["priority"] == "high"


def test_priority_derived_from_risk_score():
    """priority 应自动从 risk_score 推导。"""
    assert _derive_priority(10) == "low"
    assert _derive_priority(30) == "medium"
    assert _derive_priority(80) == "high"


def test_priority_sort_key_orders_correctly():
    """优先级排序键应正确排序。"""
    items = [
        {"priority": "low"},
        {"priority": "high"},
        {"priority": "medium"},
    ]
    items.sort(key=_priority_sort_key)
    assert items[0]["priority"] == "high"
    assert items[1]["priority"] == "medium"
    assert items[2]["priority"] == "low"
