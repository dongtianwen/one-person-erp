"""v2.1 深度报告服务测试。"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.report import Report
from app.models.template import Template
from app.core.constants import (
    REPORT_TYPE_WHITELIST,
    REPORT_LLM_FALLBACK_TEXT,
    PROJECT_REPORT_LLM_VARS,
    CUSTOMER_REPORT_LLM_VARS,
)
from app.core.llm_client import NullProvider, ExternalAPIProvider

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def db():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=StaticPool)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        yield session
    async with engine.begin() as conn:
        try:
            await conn.run_sync(Base.metadata.drop_all)
        except Exception:
            pass
    await engine.dispose()


def test_report_type_whitelist():
    assert "report_project" in REPORT_TYPE_WHITELIST
    assert "report_customer" in REPORT_TYPE_WHITELIST


def test_project_report_llm_vars():
    assert "analysis_summary" in PROJECT_REPORT_LLM_VARS
    assert "risk_retrospective" in PROJECT_REPORT_LLM_VARS
    assert "improvement_suggestions" in PROJECT_REPORT_LLM_VARS


def test_customer_report_llm_vars():
    assert "value_assessment" in CUSTOMER_REPORT_LLM_VARS
    assert "relationship_summary" in CUSTOMER_REPORT_LLM_VARS
    assert "next_action_suggestions" in CUSTOMER_REPORT_LLM_VARS


@pytest.mark.asyncio
async def test_fill_llm_vars_none_provider_uses_fallback(db):
    from app.core.report_service import fill_llm_vars

    with patch("app.core.report_service.get_llm_provider", return_value=NullProvider()):
        result = await fill_llm_vars(db, "report_project", {})
    for var in PROJECT_REPORT_LLM_VARS:
        assert result[var] == REPORT_LLM_FALLBACK_TEXT


@pytest.mark.asyncio
async def test_fill_llm_vars_api_provider_success(db):
    from app.core.report_service import fill_llm_vars

    provider = ExternalAPIProvider(api_key="test", base_url="https://api.test.com/v1", model="gpt-4o-mini")
    mock_fill = AsyncMock(return_value="AI 分析内容")
    with patch.object(provider, "_call_llm_single_var", mock_fill):
        with patch("app.core.report_service.get_llm_provider", return_value=provider):
            result = await fill_llm_vars(db, "report_project", {"project_name": "测试"})
    for var in PROJECT_REPORT_LLM_VARS:
        assert result[var] == "AI 分析内容"


@pytest.mark.asyncio
async def test_fill_llm_vars_partial_failure(db):
    from app.core.report_service import fill_llm_vars

    call_count = 0

    async def mock_fill(var_name, context, prompt):
        nonlocal call_count
        call_count += 1
        if var_name == "risk_retrospective":
            raise Exception("模拟失败")
        return "AI 分析内容"

    provider = ExternalAPIProvider(api_key="test", base_url="https://api.test.com/v1", model="gpt-4o-mini")
    with patch.object(provider, "_call_llm_single_var", side_effect=mock_fill):
        with patch("app.core.report_service.get_llm_provider", return_value=provider):
            result = await fill_llm_vars(db, "report_project", {})
    assert result["analysis_summary"] == "AI 分析内容"
    assert result["risk_retrospective"] == REPORT_LLM_FALLBACK_TEXT
    assert result["improvement_suggestions"] == "AI 分析内容"


@pytest.mark.asyncio
async def test_report_type_not_supported(db):
    from app.core.report_service import generate_report
    from app.core.exception_handlers import BusinessException

    with pytest.raises(BusinessException) as exc_info:
        await generate_report(db, "invalid_type", 1)
    assert exc_info.value.code == "REPORT_TYPE_NOT_SUPPORTED"


@pytest.mark.asyncio
async def test_report_version_increment(db):
    from app.core.report_service import generate_report

    mock_ctx = {
        "project_name": "测试项目",
        "customer_name": "测试客户",
        "generated_date": "2026-04-16",
        "start_date": "2026-01-01",
        "end_date": "2026-03-31",
        "duration_days": 90,
        "contract_amount": "100,000.00",
        "received_amount": "80,000.00",
        "pending_amount": "20,000.00",
        "total_hours": 200,
        "milestone_completion_rate": "80.0",
        "change_count": 2,
        "acceptance_passed": "已通过",
        "gross_margin_rate": "30.0",
        "direct_cost": "50,000.00",
        "outsource_cost": "10,000.00",
    }

    with patch("app.core.report_service.get_llm_provider", return_value=NullProvider()), \
         patch("app.core.report_service._build_context", return_value=mock_ctx), \
         patch("app.core.report_service._get_template_content", return_value="项目：{{ project_name }}"):
        r1 = await generate_report(db, "report_project", 1)
        assert r1["status"] == "completed"

    r1_record = await db.execute(text("SELECT version_no, is_latest FROM reports WHERE id=:id"), {"id": r1["report_id"]})
    row1 = r1_record.fetchone()
    assert row1[0] == 1
    assert row1[1] == 1

    with patch("app.core.report_service.get_llm_provider", return_value=NullProvider()), \
         patch("app.core.report_service._build_context", return_value=mock_ctx), \
         patch("app.core.report_service._get_template_content", return_value="项目：{{ project_name }}"):
        r2 = await generate_report(db, "report_project", 1)
        assert r2["status"] == "completed"

    r1_update = await db.execute(text("SELECT is_latest FROM reports WHERE id=:id"), {"id": r1["report_id"]})
    assert r1_update.fetchone()[0] == 0

    r2_record = await db.execute(text("SELECT version_no, is_latest, parent_report_id FROM reports WHERE id=:id"), {"id": r2["report_id"]})
    row2 = r2_record.fetchone()
    assert row2[0] == 2
    assert row2[1] == 1
    assert row2[2] == r1["report_id"]


@pytest.mark.asyncio
async def test_get_template_content_uses_builtin_fallback(db):
    from app.core.report_service import _get_template_content

    template = await _get_template_content(db, "report_project", None)

    assert "项目复盘报告" in template
    assert "{{ project_name }}" in template
