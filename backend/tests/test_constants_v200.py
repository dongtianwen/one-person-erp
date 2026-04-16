"""v2.0 常量验证测试。"""
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


class TestConstantsV200WhitelistCompleteness:
    """测试所有白名单常量完整。"""

    def test_llm_provider_whitelist(self):
        assert "none" in LLM_PROVIDER_WHITELIST
        assert "local" in LLM_PROVIDER_WHITELIST
        assert "api" in LLM_PROVIDER_WHITELIST

    def test_agent_type_whitelist(self):
        assert "business_decision" in AGENT_TYPE_WHITELIST
        assert "project_management" in AGENT_TYPE_WHITELIST

    def test_suggestion_type_whitelist(self):
        assert len(SUGGESTION_TYPE_WHITELIST) >= 6

    def test_suggestion_status_whitelist(self):
        assert "pending" in SUGGESTION_STATUS_WHITELIST
        assert "confirmed" in SUGGESTION_STATUS_WHITELIST
        assert "rejected" in SUGGESTION_STATUS_WHITELIST

    def test_action_type_whitelist(self):
        assert "create_todo" in ACTION_TYPE_WHITELIST
        assert "create_reminder" in ACTION_TYPE_WHITELIST
        assert "generate_report" in ACTION_TYPE_WHITELIST
        assert "none" in ACTION_TYPE_WHITELIST

    def test_action_status_whitelist(self):
        assert "pending" in ACTION_STATUS_WHITELIST
        assert "executed" in ACTION_STATUS_WHITELIST
        assert "failed" in ACTION_STATUS_WHITELIST

    def test_decision_type_whitelist(self):
        assert "accepted" in DECISION_TYPE_WHITELIST
        assert "rejected" in DECISION_TYPE_WHITELIST
        assert "modified" in DECISION_TYPE_WHITELIST

    def test_priority_whitelist(self):
        assert "high" in PRIORITY_WHITELIST
        assert "medium" in PRIORITY_WHITELIST
        assert "low" in PRIORITY_WHITELIST

    def test_agent_run_status_whitelist(self):
        assert "running" in AGENT_RUN_STATUS_WHITELIST
        assert "completed" in AGENT_RUN_STATUS_WHITELIST
        assert "failed" in AGENT_RUN_STATUS_WHITELIST

    def test_agent_trigger_type_whitelist(self):
        assert "manual" in AGENT_TRIGGER_TYPE_WHITELIST
        assert "scheduled" in AGENT_TRIGGER_TYPE_WHITELIST


class TestFeedbackWeightRules:
    """测试反馈权重规则。"""

    def test_has_all_decision_fields(self):
        assert "decision_type" in FEEDBACK_WEIGHT_RULES
        assert "reason_code" in FEEDBACK_WEIGHT_RULES
        assert "corrected_fields" in FEEDBACK_WEIGHT_RULES

    def test_all_weights_positive(self):
        for key, weight in FEEDBACK_WEIGHT_RULES.items():
            assert weight > 0, f"权重 {key}={weight} 必须为正数"

    def test_no_magic_numbers_in_weights(self):
        for key, weight in FEEDBACK_WEIGHT_RULES.items():
            assert isinstance(weight, int), f"权重 {key} 必须是整数"


class TestErrorCodesV200:
    """测试 v2.0 错误码定义。"""

    def test_v20_error_codes_exist(self):
        required_codes = [
            "OLLAMA_UNAVAILABLE",
            "API_PROVIDER_UNAVAILABLE",
            "LLM_PARSE_FAILED",
            "AGENT_ALREADY_RUNNING",
            "SUGGESTION_NOT_PENDING",
            "ACTION_EXECUTION_FAILED",
        ]
        for code in required_codes:
            assert code in ERROR_CODES, f"缺少错误码: {code}"
            assert ERROR_CODES[code], f"错误码 {code} 描述不应为空"
