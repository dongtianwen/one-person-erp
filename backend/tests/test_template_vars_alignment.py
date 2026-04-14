"""v1.12 模板变量对齐测试——验证模板使用的变量与常量定义一致。"""
import re
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    QUOTATION_REQUIRED_VARS,
    QUOTATION_OPTIONAL_VARS,
    CONTRACT_REQUIRED_VARS,
    CONTRACT_OPTIONAL_VARS,
)
from app.crud import template as template_crud
from app.core.template_utils import build_quotation_context, build_contract_context


@pytest.mark.asyncio
async def test_quotation_template_uses_only_defined_vars(db_session: AsyncSession):
    """测试报价单模板只使用定义的变量。"""
    default_template = await template_crud.get_default_template(db_session, template_type="quotation")
    assert default_template is not None

    required_vars = set(QUOTATION_REQUIRED_VARS)
    optional_vars = set(QUOTATION_OPTIONAL_VARS)
    all_defined_vars = required_vars | optional_vars

    used_vars = set()
    pattern = r'\{\{\s*(\w+)\s*\}\}'
    for match in re.finditer(pattern, default_template.content):
        used_vars.add(match.group(1))

    undefined_vars = used_vars - all_defined_vars
    assert not undefined_vars, f"报价单模板使用了未定义的变量: {undefined_vars}"

    missing_required = required_vars - used_vars
    if missing_required:
        print(f"警告: 报价单模板未使用以下必填变量: {missing_required}")


@pytest.mark.asyncio
async def test_contract_template_uses_only_defined_vars(db_session: AsyncSession):
    """测试合同模板只使用定义的变量。"""
    default_template = await template_crud.get_default_template(db_session, template_type="contract")
    assert default_template is not None

    required_vars = set(CONTRACT_REQUIRED_VARS)
    optional_vars = set(CONTRACT_OPTIONAL_VARS)
    all_defined_vars = required_vars | optional_vars

    used_vars = set()
    pattern = r'\{\{\s*(\w+)\s*\}\}'
    for match in re.finditer(pattern, default_template.content):
        used_vars.add(match.group(1))

    undefined_vars = used_vars - all_defined_vars
    assert not undefined_vars, f"合同模板使用了未定义的变量: {undefined_vars}"

    missing_required = required_vars - used_vars
    if missing_required:
        print(f"警告: 合同模板未使用以下必填变量: {missing_required}")


def test_all_defined_vars_are_documented():
    """测试所有定义的变量名非空。"""
    for var in QUOTATION_REQUIRED_VARS:
        assert var, f"报价单必填变量为空"
    for var in QUOTATION_OPTIONAL_VARS:
        assert var, f"报价单可选变量为空"
    for var in CONTRACT_REQUIRED_VARS:
        assert var, f"合同必填变量为空"
    for var in CONTRACT_OPTIONAL_VARS:
        assert var, f"合同可选变量为空"


def test_variable_names_are_consistent():
    """测试变量名在 build_context 函数和常量定义中一致。"""
    quotation_data = {
        "quotation_no": "BJ-001",
        "customer_name": "Test",
        "project_name": "Test Project",
        "requirement_summary": "Test",
        "estimate_days": 10,
        "total_amount": 10000,
        "valid_until": "2026-05-13",
        "created_date": "2026-04-13",
        "daily_rate": 500,
        "direct_cost": 3000,
        "tax_rate": 0.13,
        "tax_amount": 1300,
        "discount_amount": 0,
        "subtotal_amount": 8700,
        "notes": "Test",
        "company_name": "Test",
        "payment_terms": "Test",
        "estimate_hours": 80,
    }
    contract_data = {
        "contract_no": "HT-001",
        "customer_name": "Test",
        "project_name": "Test Project",
        "total_amount": 10000,
        "sign_date": "2026-04-13",
        "company_name": "Test",
        "quotation_no": "BJ-001",
        "payment_terms": "Test",
        "project_scope": "Test",
        "deliverables_desc": "Test",
        "acceptance_criteria": "Test",
        "liability_clause": "Test",
        "notes": "Test",
        "start_date": "2026-05-01",
        "end_date": "2026-06-30",
    }

    quotation_context = build_quotation_context(quotation_data)
    contract_context = build_contract_context(contract_data)

    for var in QUOTATION_REQUIRED_VARS:
        assert var in quotation_context, f"报价单必填变量 '{var}' 未在上下文中"
    for var in CONTRACT_REQUIRED_VARS:
        assert var in contract_context, f"合同必填变量 '{var}' 未在上下文中"

    for var in quotation_context:
        assert var in QUOTATION_REQUIRED_VARS or var in QUOTATION_OPTIONAL_VARS, \
            f"报价单上下文中存在未定义的变量: '{var}'"
    for var in contract_context:
        assert var in CONTRACT_REQUIRED_VARS or var in CONTRACT_OPTIONAL_VARS, \
            f"合同上下文中存在未定义的变量: '{var}'"
