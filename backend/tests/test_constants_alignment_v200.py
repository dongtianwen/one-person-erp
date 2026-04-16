"""v2.0 常量对齐验证——确保所有模块使用的常量与 constants.py 一致。"""
import pytest

from app.core.constants import (
    LLM_PROVIDER_WHITELIST,
    AGENT_TYPE_WHITELIST,
    SUGGESTION_TYPE_WHITELIST,
    SUGGESTION_STATUS_WHITELIST,
    ACTION_TYPE_WHITELIST,
    ACTION_STATUS_WHITELIST,
    DECISION_TYPE_WHITELIST,
    PRIORITY_WHITELIST,
    AGENT_RUN_STATUS_WHITELIST,
    AGENT_TRIGGER_TYPE_WHITELIST,
    FEEDBACK_WEIGHT_RULES,
)
from app.core.error_codes import ERROR_CODES


class TestConstantsAlignment:
    """验证各白名单包含预期值，无遗漏。"""

    def test_llm_provider_whitelist(self):
        assert "none" in LLM_PROVIDER_WHITELIST
        assert "local" in LLM_PROVIDER_WHITELIST
        assert "api" in LLM_PROVIDER_WHITELIST

    def test_agent_type_whitelist(self):
        assert "business_decision" in AGENT_TYPE_WHITELIST
        assert "project_management" in AGENT_TYPE_WHITELIST

    def test_suggestion_type_whitelist(self):
        v20_types = {
            "overdue_payment", "profit_anomaly", "milestone_risk",
            "cashflow_warning", "task_delay", "change_impact",
        }
        assert v20_types.issubset(set(SUGGESTION_TYPE_WHITELIST))

    def test_action_type_whitelist(self):
        assert "create_todo" in ACTION_TYPE_WHITELIST
        assert "create_reminder" in ACTION_TYPE_WHITELIST
        assert "generate_report" in ACTION_TYPE_WHITELIST
        assert "none" in ACTION_TYPE_WHITELIST

    def test_decision_type_whitelist(self):
        assert "accepted" in DECISION_TYPE_WHITELIST
        assert "rejected" in DECISION_TYPE_WHITELIST
        assert "modified" in DECISION_TYPE_WHITELIST

    def test_priority_whitelist(self):
        assert set(PRIORITY_WHITELIST) == {"high", "medium", "low"}

    def test_agent_run_status_whitelist(self):
        assert set(AGENT_RUN_STATUS_WHITELIST) == {"running", "completed", "failed"}

    def test_agent_trigger_type_whitelist(self):
        assert set(AGENT_TRIGGER_TYPE_WHITELIST) == {"manual", "scheduled"}

    def test_suggestion_status_whitelist(self):
        assert set(SUGGESTION_STATUS_WHITELIST) == {"pending", "confirmed", "rejected"}

    def test_action_status_whitelist(self):
        assert set(ACTION_STATUS_WHITELIST) == {"pending", "executed", "failed"}


class TestFeedbackWeightRules:
    """验证反馈权重规则合理性。"""

    def test_all_fields_have_positive_weight(self):
        for field, weight in FEEDBACK_WEIGHT_RULES.items():
            assert weight > 0, f"{field} 权重应为正数"

    def test_max_possible_weight(self):
        total = sum(FEEDBACK_WEIGHT_RULES.values())
        assert total >= 5, f"总权重应 >= 5，实际 {total}"

    def test_has_decision_type_weight(self):
        assert "decision_type" in FEEDBACK_WEIGHT_RULES
        assert FEEDBACK_WEIGHT_RULES["decision_type"] >= 2


class TestErrorCodesV20:
    """验证 v2.0 错误码存在且非空。"""

    def test_llm_error_codes(self):
        assert "OLLAMA_UNAVAILABLE" in ERROR_CODES
        assert "API_PROVIDER_UNAVAILABLE" in ERROR_CODES
        assert "LLM_PARSE_FAILED" in ERROR_CODES

    def test_agent_error_codes(self):
        assert "AGENT_ALREADY_RUNNING" in ERROR_CODES
        assert "SUGGESTION_NOT_PENDING" in ERROR_CODES
        assert "ACTION_EXECUTION_FAILED" in ERROR_CODES

    def test_error_codes_not_empty_string(self):
        for key in ["OLLAMA_UNAVAILABLE", "API_PROVIDER_UNAVAILABLE", "LLM_PARSE_FAILED",
                     "AGENT_ALREADY_RUNNING", "SUGGESTION_NOT_PENDING", "ACTION_EXECUTION_FAILED"]:
            assert ERROR_CODES[key], f"错误码 {key} 的值不应为空"
