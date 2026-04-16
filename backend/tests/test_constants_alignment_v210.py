"""v2.1 常量对齐验证测试。"""
import pytest
from app.core.constants import (
    TEMPLATE_TYPE_WHITELIST,
    AGENT_TYPE_WHITELIST,
    SUGGESTION_TYPE_WHITELIST,
    REPORT_TYPE_WHITELIST,
    TEMPLATE_TYPE_REPORT_PROJECT,
    TEMPLATE_TYPE_REPORT_CUSTOMER,
    AGENT_TYPE_DELIVERY_QC,
    SUGGESTION_TYPE_DELIVERY_MISSING_MODEL,
    SUGGESTION_TYPE_DELIVERY_MISSING_DATASET,
    SUGGESTION_TYPE_DELIVERY_MISSING_ACCEPTANCE,
    SUGGESTION_TYPE_DELIVERY_VERSION_MISMATCH,
    SUGGESTION_TYPE_DELIVERY_EMPTY_PACKAGE,
    SUGGESTION_TYPE_DELIVERY_UNBOUND_PROJECT,
    REPORT_TYPE_PROJECT,
    REPORT_TYPE_CUSTOMER,
    REPORT_STATUS_GENERATING,
    REPORT_STATUS_COMPLETED,
    REPORT_STATUS_FAILED,
    PROJECT_REPORT_LLM_VARS,
    CUSTOMER_REPORT_LLM_VARS,
    REPORT_LLM_FALLBACK_TEXT,
    QA_CONTEXT_MONTHS,
    QA_CONTEXT_MAX_PROJECTS,
    QA_CONTEXT_MAX_TOKENS_ESTIMATE,
    QA_MAX_HISTORY_TURNS,
)
from app.core.llm_client import NullProvider, OllamaProvider, ExternalAPIProvider
from app.core.error_codes import ERROR_CODES


def test_template_whitelist_includes_report_types():
    assert TEMPLATE_TYPE_REPORT_PROJECT in TEMPLATE_TYPE_WHITELIST
    assert TEMPLATE_TYPE_REPORT_CUSTOMER in TEMPLATE_TYPE_WHITELIST


def test_agent_whitelist_includes_delivery_qc():
    assert AGENT_TYPE_DELIVERY_QC in AGENT_TYPE_WHITELIST


def test_suggestion_whitelist_includes_delivery_types():
    delivery_types = [
        SUGGESTION_TYPE_DELIVERY_MISSING_MODEL,
        SUGGESTION_TYPE_DELIVERY_MISSING_DATASET,
        SUGGESTION_TYPE_DELIVERY_MISSING_ACCEPTANCE,
        SUGGESTION_TYPE_DELIVERY_VERSION_MISMATCH,
        SUGGESTION_TYPE_DELIVERY_EMPTY_PACKAGE,
        SUGGESTION_TYPE_DELIVERY_UNBOUND_PROJECT,
    ]
    for t in delivery_types:
        assert t in SUGGESTION_TYPE_WHITELIST


def test_report_type_whitelist_matches_template_types():
    assert REPORT_TYPE_PROJECT == TEMPLATE_TYPE_REPORT_PROJECT
    assert REPORT_TYPE_CUSTOMER == TEMPLATE_TYPE_REPORT_CUSTOMER


def test_report_status_constants():
    assert REPORT_STATUS_GENERATING == "generating"
    assert REPORT_STATUS_COMPLETED == "completed"
    assert REPORT_STATUS_FAILED == "failed"


def test_llm_vars_defined():
    assert len(PROJECT_REPORT_LLM_VARS) == 3
    assert len(CUSTOMER_REPORT_LLM_VARS) == 3


def test_qa_constants_reasonable():
    assert QA_CONTEXT_MONTHS > 0
    assert QA_CONTEXT_MAX_PROJECTS > 0
    assert QA_CONTEXT_MAX_TOKENS_ESTIMATE > 0
    assert QA_MAX_HISTORY_TURNS > 0


def test_fallback_text_not_empty():
    assert len(REPORT_LLM_FALLBACK_TEXT) > 0


def test_error_codes_v21_registered():
    v21_codes = [
        "QA_REQUIRES_API_PROVIDER",
        "QA_CONTEXT_BUILD_FAILED",
        "REPORT_TYPE_NOT_SUPPORTED",
        "REPORT_ENTITY_NOT_FOUND",
        "REPORT_LLM_FILL_FAILED",
        "DELIVERY_QC_NO_PACKAGE",
    ]
    for code in v21_codes:
        assert code in ERROR_CODES


def test_null_provider_no_freeform():
    assert not hasattr(NullProvider, "call_freeform")
    assert not hasattr(NullProvider, "_call_llm_single_var")


def test_ollama_provider_no_freeform():
    assert not hasattr(OllamaProvider, "call_freeform")
    assert not hasattr(OllamaProvider, "_call_llm_single_var")


def test_external_api_provider_has_methods():
    assert hasattr(ExternalAPIProvider, "call_freeform")
    assert hasattr(ExternalAPIProvider, "_call_llm_single_var")
    assert hasattr(ExternalAPIProvider, "is_available")
