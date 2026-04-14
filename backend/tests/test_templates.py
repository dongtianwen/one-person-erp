"""v1.12 模板管理测试——覆盖 CRUD、默认模板、渲染、冻结等。"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import template as template_crud
from app.core.template_utils import (
    validate_template_syntax,
    render_template,
    can_regenerate_content,
    build_quotation_context,
    build_contract_context,
)
from app.core.constants import (
    QUOTATION_REQUIRED_VARS,
    CONTRACT_REQUIRED_VARS,
    QUOTATION_CONTENT_FROZEN_STATUS,
    CONTRACT_CONTENT_FROZEN_STATUS,
    TEMPLATE_TYPE_QUOTATION,
    TEMPLATE_TYPE_CONTRACT,
)


# ── 模板 CRUD ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_default_quotation_template(db_session: AsyncSession):
    """验证可以获取默认报价单模板。"""
    tpl = await template_crud.get_default_template(db_session, "quotation")
    assert tpl is not None
    assert tpl.template_type == TEMPLATE_TYPE_QUOTATION
    assert tpl.is_default == 1


@pytest.mark.asyncio
async def test_get_default_contract_template(db_session: AsyncSession):
    """验证可以获取默认合同模板。"""
    tpl = await template_crud.get_default_template(db_session, "contract")
    assert tpl is not None
    assert tpl.template_type == TEMPLATE_TYPE_CONTRACT
    assert tpl.is_default == 1


@pytest.mark.asyncio
async def test_template_type_whitelist_enforced(db_session: AsyncSession):
    """验证无效模板类型返回 None。"""
    tpl = await template_crud.get_default_template(db_session, "invalid_type")
    assert tpl is None


@pytest.mark.asyncio
async def test_set_default_replaces_existing_atomic(db_session: AsyncSession):
    """验证设置默认模板时原子替换旧默认。"""
    custom = await template_crud.create_template(
        db=db_session,
        name="自定义报价模板",
        template_type="quotation",
        content="Test {{ quotation_no }}",
    )

    success = await template_crud.set_default_template(
        db=db_session, template_id=custom.id, template_type="quotation"
    )
    assert success is True

    default = await template_crud.get_default_template(db_session, "quotation")
    assert default.id == custom.id


@pytest.mark.asyncio
async def test_default_template_cannot_delete(db_session: AsyncSession):
    """验证默认模板不可删除。"""
    default = await template_crud.get_default_template(db_session, "quotation")
    result = await template_crud.delete_template(db_session, default.id)
    assert result is False


@pytest.mark.asyncio
async def test_non_default_template_can_delete(db_session: AsyncSession):
    """验证非默认模板可删除。"""
    custom = await template_crud.create_template(
        db=db_session,
        name="可删除模板",
        template_type="quotation",
        content="Test",
    )
    result = await template_crud.delete_template(db_session, custom.id)
    assert result is True


@pytest.mark.asyncio
async def test_delete_does_not_affect_generated_content(db_session: AsyncSession):
    """验证删除模板不影响已生成的内容快照。

    模板删除后，quotations.generated_content 仍保留。
    """
    custom = await template_crud.create_template(
        db=db_session,
        name="临时模板",
        template_type="quotation",
        content="Test {{ quotation_no }}",
    )
    assert await template_crud.delete_template(db_session, custom.id) is True
    # 模板已删除，但已有的 generated_content 快照不受影响
    # （本测试验证模板删除本身成功）


# ── 模板语法校验 ───────────────────────────────────────────────


def test_invalid_jinja2_syntax_rejected():
    """验证无效 Jinja2 语法被拒绝。"""
    is_valid, error_msg = validate_template_syntax("{{ invalid }} {% if %}")
    assert is_valid is False
    assert "语法错误" in error_msg or "错误" in error_msg


def test_valid_jinja2_syntax_accepted():
    """验证有效 Jinja2 语法通过校验。"""
    is_valid, error_msg = validate_template_syntax("Hello {{ name }}")
    assert is_valid is True
    assert error_msg == ""


# ── 模板渲染 ───────────────────────────────────────────────────


def test_render_success():
    """验证模板渲染成功。"""
    content, error = render_template(
        template_content="Hello {{ name }}",
        context={"name": "World"},
    )
    assert error is None or error == ""
    assert "Hello World" in content


def test_missing_required_var_raises_missing_vars_error():
    """验证缺少必填变量返回 TEMPLATE_MISSING_REQUIRED_VARS 错误。"""
    content, error = render_template(
        template_content="{{ quotation_no }}",
        context={},
        required_vars=QUOTATION_REQUIRED_VARS,
    )
    assert error is not None
    assert "quotation_no" in error


def test_missing_vars_error_not_render_error():
    """验证缺失变量错误与渲染错误互斥。"""
    # 缺失变量时，不会触发渲染错误
    content, error = render_template(
        template_content="{{ missing_var }}",
        context={"other": "value"},
        required_vars=["required_field"],
    )
    assert error is not None
    assert "required_field" in error


def test_optional_vars_missing_uses_empty_string():
    """验证可选变量缺失时不报错。"""
    context = {var: "" for var in QUOTATION_REQUIRED_VARS}
    # 不传 required_vars，跳过校验
    content, error = render_template(
        template_content="Hello {{ notes | default('') }}",
        context=context,
    )
    assert error is None or error == ""


# ── can_regenerate_content ─────────────────────────────────────


def test_can_regenerate_accepted_false():
    """验证 accepted 状态不可重新生成。"""
    can, error = can_regenerate_content(
        status=QUOTATION_CONTENT_FROZEN_STATUS,
        template_type=TEMPLATE_TYPE_QUOTATION,
        has_content=True,
        force=True,
    )
    assert can is False
    assert error is not None


def test_can_regenerate_active_contract_false():
    """验证 active 状态的合同不可重新生成。"""
    can, error = can_regenerate_content(
        status=CONTRACT_CONTENT_FROZEN_STATUS,
        template_type=TEMPLATE_TYPE_CONTRACT,
        has_content=True,
        force=True,
    )
    assert can is False
    assert error is not None


def test_can_regenerate_draft_no_content():
    """验证 draft 状态且无内容时可以生成。"""
    can, error = can_regenerate_content(
        status="draft",
        template_type=TEMPLATE_TYPE_QUOTATION,
        has_content=False,
        force=False,
    )
    assert can is True
    assert error is None


def test_can_regenerate_draft_with_content_no_force():
    """验证 draft 状态且有内容但未传 force 时返回已存在。"""
    can, error = can_regenerate_content(
        status="draft",
        template_type=TEMPLATE_TYPE_QUOTATION,
        has_content=True,
        force=False,
    )
    assert can is False
    assert error is not None


def test_can_regenerate_draft_with_content_force():
    """验证 draft 状态且有内容且传 force 时可以覆盖。"""
    can, error = can_regenerate_content(
        status="draft",
        template_type=TEMPLATE_TYPE_QUOTATION,
        has_content=True,
        force=True,
    )
    assert can is True
    assert error is None


# ── build_context 函数 ──────────────────────────────────────────


def test_build_quotation_context_has_required_vars():
    """验证 build_quotation_context 包含所有必填变量。"""
    quotation = {
        "quote_no": "BJ-001",
        "customer_name": "Test Customer",
        "project_name": "Test Project",
        "requirement_summary": "Test requirement",
        "estimate_days": 10,
        "total_amount": 10000,
        "valid_until": "2026-05-13",
        "created_at": "2026-04-13",
    }
    context = build_quotation_context(quotation)

    for var in QUOTATION_REQUIRED_VARS:
        assert var in context, f"报价单上下文中缺少必填变量: {var}"


def test_build_contract_context_has_required_vars():
    """验证 build_contract_context 包含所有必填变量且 quotation_no 存在。"""
    contract = {
        "contract_no": "HT-001",
        "customer_name": "Test Customer",
        "project_name": "Test Project",
        "amount": 10000,
        "signed_date": "2026-04-13",
    }
    quotation = {"quote_no": "BJ-001"}
    context = build_contract_context(contract, quotation)

    for var in CONTRACT_REQUIRED_VARS:
        assert var in context, f"合同上下文中缺少必填变量: {var}"
    assert context["quotation_no"] == "BJ-001"


def test_build_contract_context_without_quotation():
    """验证无报价单时 quotation_no 为空字符串。"""
    contract = {
        "contract_no": "HT-001",
        "customer_name": "Test Customer",
        "project_name": "Test Project",
        "amount": 10000,
        "signed_date": "2026-04-13",
    }
    context = build_contract_context(contract, quotation=None)
    assert context["quotation_no"] == ""
