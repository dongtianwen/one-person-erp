"""v2.2 处置策略库测试。"""
import pytest
from app.core.agent_rules import (
    _match_strategy,
    ACTION_STRATEGY_LIBRARY,
    _derive_priority,
)


class TestStrategyLibrary:
    """处置策略库测试。"""

    def test_all_strategies_exist(self):
        assert "light_reminder" in ACTION_STRATEGY_LIBRARY
        assert "escalated_reminder" in ACTION_STRATEGY_LIBRARY
        assert "management_escalation" in ACTION_STRATEGY_LIBRARY
        assert "delivery_suspension" in ACTION_STRATEGY_LIBRARY

    def test_strategy_structure(self):
        for code, template in ACTION_STRATEGY_LIBRARY.items():
            assert "strategy_code" in template
            assert "strategy_name" in template
            assert "action_steps" in template
            assert "owner" in template
            assert "deadline" in template
            assert isinstance(template["action_steps"], list)
            assert len(template["action_steps"]) > 0

    def test_match_strategy_light_reminder(self):
        strategy = _match_strategy(10)
        assert strategy["strategy_code"] == "light_reminder"
        assert strategy["strategy_name"] == "轻度催收"

    def test_match_strategy_escalated_reminder(self):
        strategy = _match_strategy(40)
        assert strategy["strategy_code"] == "escalated_reminder"

    def test_match_strategy_management_escalation(self):
        strategy = _match_strategy(60)
        assert strategy["strategy_code"] == "management_escalation"

    def test_match_strategy_delivery_suspension(self):
        strategy = _match_strategy(90)
        assert strategy["strategy_code"] == "delivery_suspension"

    def test_boundary_scores(self):
        assert _match_strategy(0)["strategy_code"] == "light_reminder"
        assert _match_strategy(25)["strategy_code"] == "light_reminder"
        assert _match_strategy(26)["strategy_code"] == "escalated_reminder"
        assert _match_strategy(50)["strategy_code"] == "escalated_reminder"
        assert _match_strategy(51)["strategy_code"] == "management_escalation"
        assert _match_strategy(75)["strategy_code"] == "management_escalation"
        assert _match_strategy(76)["strategy_code"] == "delivery_suspension"
        assert _match_strategy(100)["strategy_code"] == "delivery_suspension"


class TestDerivePriority:
    """优先级推导测试。"""

    def test_low_priority(self):
        assert _derive_priority(0) == "low"
        assert _derive_priority(10) == "low"
        assert _derive_priority(25) == "low"

    def test_medium_priority(self):
        assert _derive_priority(26) == "medium"
        assert _derive_priority(40) == "medium"
        assert _derive_priority(50) == "medium"

    def test_high_priority(self):
        assert _derive_priority(51) == "high"
        assert _derive_priority(80) == "high"
        assert _derive_priority(100) == "high"
