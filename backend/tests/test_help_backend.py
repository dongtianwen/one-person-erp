"""v1.10 帮助系统后端测试——覆盖 build_error_response / get_help 核心逻辑。"""

import pytest

from app.core.error_codes import ERROR_CODES
from app.core.help_content import HELP_CONTENT, get_help
from app.core.exception_handlers import build_error_response


# ── get_help 基础测试 ─────────────────────────────────────────


def test_get_help_returns_none_for_unknown_code():
    """无映射的错误码返回 None。"""
    assert get_help("UNKNOWN_CODE_XYZ") is None


def test_get_help_returns_correct_structure():
    """有映射的错误码返回 reason + next_steps。"""
    result = get_help("REQUIREMENT_FROZEN")
    assert result is not None
    assert "reason" in result
    assert "next_steps" in result
    assert isinstance(result["next_steps"], list)
    assert len(result["next_steps"]) > 0


def test_get_help_includes_doc_anchor():
    """有 doc_anchor 的错误码应包含该字段。"""
    result = get_help("REQUIREMENT_FROZEN")
    assert result is not None
    assert "doc_anchor" in result
    assert result["doc_anchor"] == "change-order-flow"


# ── next_steps 截断测试 ──────────────────────────────────────


def test_help_next_steps_capped_at_max():
    """next_steps 数量不超过 HELP_MAX_NEXT_STEPS。"""
    from app.core.constants import HELP_MAX_NEXT_STEPS

    # PROJECT_CLOSE_CONDITIONS_NOT_MET 有 5 个步骤，恰好等于上限
    result = get_help("PROJECT_CLOSE_CONDITIONS_NOT_MET")
    assert result is not None
    assert len(result["next_steps"]) <= HELP_MAX_NEXT_STEPS


# ── build_error_response 测试 ────────────────────────────────


def test_error_response_includes_help_when_code_matched():
    """有映射的错误码，响应包含 help 字段。"""
    resp = build_error_response("需求已冻结，请通过变更单提交", "REQUIREMENT_FROZEN")
    assert "help" in resp
    assert resp["help"]["reason"] != ""


def test_error_response_no_help_when_code_not_in_mapping():
    """无映射的错误码，响应不包含 help 字段。"""
    resp = build_error_response("记录不存在", "NOT_FOUND")
    assert "help" not in resp


def test_detail_not_modified_by_help_injection():
    """help 注入不修改 detail 内容。"""
    original_detail = "需求已冻结，请通过变更单提交"
    resp = build_error_response(original_detail, "REQUIREMENT_FROZEN")
    assert resp["detail"] == original_detail


def test_code_not_modified_by_help_injection():
    """help 注入不修改 code 内容。"""
    original_code = "REQUIREMENT_FROZEN"
    resp = build_error_response("需求已冻结", original_code)
    assert resp["code"] == original_code


# ── 具体错误码帮助内容正确性测试 ──────────────────────────────


def test_requirement_frozen_returns_correct_help():
    result = get_help("REQUIREMENT_FROZEN")
    assert result is not None
    assert "冻结" in result["reason"]
    assert any("变更单" in step for step in result["next_steps"])


def test_invoice_amount_exceeds_returns_correct_help():
    result = get_help("INVOICE_AMOUNT_EXCEEDS_CONTRACT")
    assert result is not None
    assert "合同" in result["reason"]


def test_project_close_not_met_returns_correct_help():
    result = get_help("PROJECT_CLOSE_CONDITIONS_NOT_MET")
    assert result is not None
    assert "前置条件" in result["reason"] or "条件未满足" in result["reason"]


def test_milestone_not_completed_returns_correct_help():
    result = get_help("MILESTONE_NOT_COMPLETED")
    assert result is not None
    assert "里程碑" in result["reason"]


# ── 5xx 错误不应附加 help（通过不调用 build_error_response 保证）──


def test_5xx_error_does_not_include_help():
    """5xx 不应经过 build_error_response，本测试验证该函数本身不会对 5xx 特殊处理。
    实际防护在异常处理器层面——HTTPException 不走 help 注入。
    """
    # build_error_response 本身不过滤状态码，但 5xx 场景不调用此函数
    # 此测试验证函数本身对任意 code 仍能正常工作
    resp = build_error_response("服务器内部错误", "INTERNAL_ERROR")
    assert "detail" in resp
    assert "code" in resp
    assert "help" not in resp  # INTERNAL_ERROR 不在 HELP_CONTENT 中


# ── HELP_CONTENT 覆盖率验证 ──────────────────────────────────


def test_all_help_content_entries_have_required_fields():
    """每条帮助内容必须包含 reason 和 next_steps。"""
    for code, content in HELP_CONTENT.items():
        assert "reason" in content, f"{code} 缺少 reason"
        assert "next_steps" in content, f"{code} 缺少 next_steps"
        assert isinstance(content["next_steps"], list), f"{code} next_steps 必须为列表"
        assert len(content["next_steps"]) > 0, f"{code} next_steps 不能为空"


def test_error_codes_covered_by_help():
    """验证 10 个需要 help 映射的错误码全部存在。"""
    required_codes = [
        "REQUIREMENT_FROZEN",
        "CHANGE_ORDER_INVALID_TRANSITION",
        "MILESTONE_NOT_COMPLETED",
        "PROJECT_CLOSE_CONDITIONS_NOT_MET",
        "PROJECT_ALREADY_CLOSED",
        "INVOICE_AMOUNT_EXCEEDS_CONTRACT",
        "INVOICE_STATUS_INVALID_TRANSITION",
        "INVOICE_CANNOT_DELETE",
        "QUOTE_ALREADY_CONVERTED",
        "QUOTE_NOT_ACCEPTED",
    ]
    for code in required_codes:
        assert code in HELP_CONTENT, f"错误码 {code} 缺少帮助映射"
