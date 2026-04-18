"""v2.0 LLM Provider 测试。"""

import pytest
import os
import sys
from unittest.mock import patch, MagicMock
from app.core.llm_client import (
    NullProvider,
    OllamaProvider,
    ExternalAPIProvider,
    _try_parse_llm_json,
    build_llm_context,
    get_llm_provider,
    _calc_feedback_weight,
)


class TestLLMProviderFactory:
    """测试工厂函数——通过 config 参数和环境变量 mock 验证。"""

    def test_config_none_provider(self):
        provider = get_llm_provider(config={"provider": "none"})
        assert isinstance(provider, NullProvider)

    def test_config_local_provider(self):
        provider = get_llm_provider(config={
            "provider": "local",
            "local_model": "test-model",
            "local_base_url": "http://test:11434",
        })
        assert isinstance(provider, OllamaProvider)
        assert provider.get_model_name() == "local:test-model"

    def test_config_api_provider(self):
        provider = get_llm_provider(config={
            "provider": "api",
            "api_key": "test-key",
            "api_base": "https://test.api/v1",
            "api_model": "test-model",
        })
        assert isinstance(provider, ExternalAPIProvider)
        assert provider.get_model_name() == "api:test-model"

    def test_config_unknown_defaults_to_null(self):
        provider = get_llm_provider(config={"provider": "unknown"})
        assert isinstance(provider, NullProvider)

    def test_env_default_is_none(self, monkeypatch):
        monkeypatch.delenv("LLM_PROVIDER", raising=False)
        mock_settings = MagicMock()
        mock_settings.LLM_PROVIDER = "none"
        with patch("app.core.llm_client.os.environ.get", return_value=None), \
             patch("app.core.llm_client.getattr", return_value="none"):
            provider = get_llm_provider()
            assert isinstance(provider, NullProvider)

    def test_env_local_provider(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "local")
        monkeypatch.setenv("LLM_LOCAL_MODEL", "env-model")
        monkeypatch.setenv("LLM_LOCAL_BASE_URL", "http://env:11434")
        mock_settings = MagicMock()
        mock_settings.LLM_PROVIDER = "local"
        mock_settings.LLM_LOCAL_MODEL = "env-model"
        with patch("app.core.llm_client.os.environ.get") as mock_env, \
             patch("app.core.llm_client.getattr", side_effect=lambda obj, name, default=None: getattr(mock_settings, name, default)):
            mock_env.side_effect = lambda key, default=None: {
                "LLM_PROVIDER": "local",
                "LLM_LOCAL_MODEL": "env-model",
                "LLM_LOCAL_BASE_URL": "http://env:11434",
            }.get(key, default)
            provider = get_llm_provider()
            assert isinstance(provider, OllamaProvider)


class TestNullProvider:
    """测试 none 档 Provider。"""

    @pytest.mark.asyncio
    async def test_enhance_returns_none(self):
        provider = NullProvider()
        result = await provider.enhance("test rule text")
        assert result is None

    def test_model_name(self):
        assert NullProvider().get_model_name() == "none"


class TestTryParseLLMJson:
    """测试 JSON 解析三步策略。"""

    def test_direct_parse_valid_json(self):
        result = _try_parse_llm_json('[{"title": "t", "description": "d"}]')
        assert result == [{"title": "t", "description": "d"}]

    def test_extract_from_markdown_fence(self):
        content = '```json\n[{"title": "t"}]\n```'
        result = _try_parse_llm_json(content)
        assert result == [{"title": "t"}]

    def test_extract_with_prefix_text(self):
        content = '好的，这是结果：\n[{"title": "t"}]'
        result = _try_parse_llm_json(content)
        assert result == [{"title": "t"}]

    def test_returns_none_on_invalid_json(self):
        assert _try_parse_llm_json("这不是JSON") is None

    def test_returns_none_on_empty(self):
        assert _try_parse_llm_json("") is None
        assert _try_parse_llm_json("   ") is None

    def test_returns_none_on_non_list_json(self):
        assert _try_parse_llm_json('{"key": "value"}') is None


class TestBuildLLMContext:
    """测试上下文构建。"""

    def test_no_feedback(self):
        ctx = build_llm_context([{"title": "test"}])
        assert "rule_text" in ctx
        assert "feedback_text" in ctx
        assert "无历史反馈记录" in ctx["feedback_text"]

    def test_empty_rules(self):
        ctx = build_llm_context([])
        assert "无异常检测" in ctx["rule_text"]

    def test_dedup_by_decision_suggestion_type(self):
        feedback = [
            {"decision_type": "overdue", "suggestion_type": "payment", "reason": "first"},
            {"decision_type": "overdue", "suggestion_type": "payment", "reason": "second"},
            {"decision_type": "risk", "suggestion_type": "milestone", "reason": "third"},
        ]
        ctx = build_llm_context([], feedback)
        # 应该只有 2 条（去重后）
        assert ctx["feedback_text"].count("overdue/payment") == 1
        assert ctx["feedback_text"].count("risk/milestone") == 1

    def test_max_records_limit(self):
        from app.core.constants import FEEDBACK_CONTEXT_MAX_RECORDS

        feedback = [{"decision_type": f"type_{i}", "suggestion_type": f"sug_{i}"} for i in range(50)]
        ctx = build_llm_context([], feedback)
        # 去重后不应超过 FEEDBACK_CONTEXT_MAX_RECORDS 条
        line_count = ctx["feedback_text"].strip().count("\n") + 1 if ctx["feedback_text"].strip() else 0
        assert line_count <= FEEDBACK_CONTEXT_MAX_RECORDS

    def test_details_injected_into_description(self):
        rules = [
            {
                "decision_type": "overdue_payment",
                "suggestion_type": "overdue_payment",
                "title": "test",
                "description": "original desc",
                "priority": "high",
                "data": {
                    "details": [
                        {
                            "project_name": "ProjectA",
                            "customer_name": "CustA",
                            "title": "M1",
                            "amount": 240000,
                            "days_overdue": 30,
                            "customer_risk_level": "normal",
                        },
                        {
                            "project_name": "ProjectB",
                            "customer_name": "CustB",
                            "title": "M2",
                            "amount": 320000,
                            "days_overdue": 7,
                            "customer_risk_level": "high",
                        },
                    ]
                },
            }
        ]
        ctx = build_llm_context(rules)
        assert "明细数据" in ctx["rule_text"]
        assert "ProjectA" in ctx["rule_text"]
        assert "ProjectB" in ctx["rule_text"]
        assert "30 天" in ctx["rule_text"]
        assert "7 天" in ctx["rule_text"]
        assert "¥240,000.00" in ctx["rule_text"]
        assert "¥320,000.00" in ctx["rule_text"]
        assert "正常" in ctx["rule_text"]
        assert "高" in ctx["rule_text"]

    def test_details_with_string_data_field(self):
        import json
        rules = [
            {
                "decision_type": "overdue_payment",
                "suggestion_type": "overdue_payment",
                "title": "test",
                "description": "original desc",
                "priority": "high",
                "data": json.dumps({
                    "details": [
                        {
                            "project_name": "ProjX",
                            "customer_name": "CustX",
                            "title": "Milestone1",
                            "amount": 50000,
                            "days_overdue": 15,
                            "customer_risk_level": "elevated",
                        }
                    ]
                }),
            }
        ]
        ctx = build_llm_context(rules)
        assert "ProjX" in ctx["rule_text"]
        assert "较高" in ctx["rule_text"]

    def test_no_details_when_details_missing(self):
        rules = [
            {
                "decision_type": "profit_anomaly",
                "suggestion_type": "profit_anomaly",
                "title": "test",
                "description": "original desc",
                "priority": "medium",
                "data": {"margin_percent": -10},
            }
        ]
        ctx = build_llm_context(rules)
        assert "明细数据" not in ctx["rule_text"]


class TestCalcFeedbackWeight:
    """测试反馈权重计算。"""

    def test_empty_record_zero_weight(self):
        assert _calc_feedback_weight({}) == 0

    def test_full_record_weight(self):
        rec = {
            "decision_type": "accepted",
            "reason_code": "confirmed",
            "corrected_fields": '{"priority": "high"}',
            "free_text_reason": "important",
            "user_priority_override": "high",
        }
        weight = _calc_feedback_weight(rec)
        assert weight > 0
