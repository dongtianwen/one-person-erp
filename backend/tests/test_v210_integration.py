"""v2.1 集成测试。"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
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


@pytest.mark.asyncio
async def test_qa_endpoint_403_on_none_provider(db):
    from app.core.qa_service import ask_question
    from app.core.exception_handlers import BusinessException

    with patch("app.core.qa_service.get_llm_provider", return_value=NullProvider()):
        with pytest.raises(BusinessException) as exc_info:
            await ask_question(db, "测试问题")
        assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_qa_history_truncation_integration(db):
    from app.core.qa_service import ask_question
    from app.core.constants import QA_MAX_HISTORY_TURNS

    provider = ExternalAPIProvider(api_key="test", base_url="https://api.test.com/v1", model="gpt-4o-mini")
    mock_freeform = AsyncMock(return_value="回答")
    long_history = [{"role": "user", "content": f"Q{i}"} for i in range(30)]

    with patch.object(provider, "call_freeform", mock_freeform):
        with patch("app.core.qa_service.get_llm_provider", return_value=provider):
            with patch("app.core.qa_service.build_qa_context", return_value={"today": "2026-04-16"}):
                result = await ask_question(db, "新问题", long_history)

    assert result["answer"] == "回答"
    messages = mock_freeform.call_args[0][0]
    non_system = [m for m in messages if m["role"] != "system"]
    assert len(non_system) <= QA_MAX_HISTORY_TURNS * 2 + 1


@pytest.mark.asyncio
async def test_report_generation_none_provider(db):
    from app.core.report_service import generate_report

    mock_ctx = {
        "project_name": "集成测试项目",
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
         patch("app.core.report_service._get_template_content", return_value="项目：{{ project_name }}\n分析：{{ analysis_summary }}"):
        result = await generate_report(db, "report_project", 1)
        assert result["status"] == "completed"
        assert result["content"] is not None


@pytest.mark.asyncio
async def test_report_generation_partial_llm_failure(db):
    from app.core.report_service import generate_report

    provider = ExternalAPIProvider(api_key="test", base_url="https://api.test.com/v1", model="gpt-4o-mini")

    async def mock_fill(var_name, context, prompt):
        if var_name == "risk_retrospective":
            raise Exception("模拟 LLM 失败")
        return "AI 分析内容"

    mock_ctx = {
        "project_name": "部分失败测试",
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

    with patch.object(provider, "_call_llm_single_var", side_effect=mock_fill):
        with patch("app.core.report_service.get_llm_provider", return_value=provider):
            with patch("app.core.report_service._build_context", return_value=mock_ctx):
                with patch("app.core.report_service._get_template_content", return_value="项目：{{ project_name }}\n分析：{{ analysis_summary }}"):
                    result = await generate_report(db, "report_project", 1)
                    assert result["status"] == "completed"


@pytest.mark.asyncio
async def test_delivery_qc_full_flow(db):
    from app.core.agent_rules import evaluate_delivery_package
    from app.models.delivery_package import DeliveryPackage
    from app.models.customer import Customer
    from app.models.project import Project

    customer = Customer(name="质检集成客户", contact_person="张三")
    db.add(customer)
    await db.flush()
    project = Project(name="质检集成项目", customer_id=customer.id, budget=100000)
    db.add(project)
    await db.flush()

    pkg = DeliveryPackage(name="集成测试交付包", status="draft", project_id=project.id)
    db.add(pkg)
    await db.commit()

    with patch("app.core.agent_rules._has_model_version", return_value=False), \
         patch("app.core.agent_rules._has_dataset_version", return_value=False), \
         patch("app.core.agent_rules._has_acceptance_record", return_value=False), \
         patch("app.core.agent_rules._has_deprecated_model", return_value=False), \
         patch("app.core.agent_rules._is_empty_package", return_value=True):
        suggestions = await evaluate_delivery_package(db, pkg.id)

    assert len(suggestions) > 0
    types = [s["suggestion_type"] for s in suggestions]
    assert "delivery_missing_model" in types
    assert "delivery_missing_dataset" in types
