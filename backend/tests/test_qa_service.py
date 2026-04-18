"""v2.1 自由问答服务测试。"""
from datetime import date
import json
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.customer import Customer
from app.models.project import Project
from app.models.contract import Contract
from app.models.setting import SystemSetting
from app.core.constants import QA_MAX_HISTORY_TURNS
from app.core.llm_client import NullProvider, OllamaProvider, ExternalAPIProvider

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


def test_call_freeform_not_on_null_provider():
    assert not hasattr(NullProvider, "call_freeform")


def test_call_freeform_not_on_ollama_provider():
    assert not hasattr(OllamaProvider, "call_freeform")


def test_call_llm_single_var_not_on_null_provider():
    assert not hasattr(NullProvider, "_call_llm_single_var")


def test_external_api_provider_has_call_freeform():
    assert hasattr(ExternalAPIProvider, "call_freeform")
    assert callable(getattr(ExternalAPIProvider, "call_freeform"))


def test_external_api_provider_has_call_llm_single_var():
    assert hasattr(ExternalAPIProvider, "_call_llm_single_var")
    assert callable(getattr(ExternalAPIProvider, "_call_llm_single_var"))


def test_external_api_provider_is_available():
    provider = ExternalAPIProvider(api_key="test", base_url="https://api.test.com/v1", model="gpt-4o-mini")
    assert provider.is_available() is True

    provider_no_key = ExternalAPIProvider(api_key="", base_url="https://api.test.com/v1", model="gpt-4o-mini")
    assert provider_no_key.is_available() is False

    provider_no_url = ExternalAPIProvider(api_key="test", base_url="", model="gpt-4o-mini")
    assert provider_no_url.is_available() is False


@pytest.mark.asyncio
async def test_qa_requires_api_provider(db):
    from app.core.qa_service import ask_question
    from app.core.exception_handlers import BusinessException

    with patch("app.core.qa_service.get_llm_provider", return_value=NullProvider()):
        with pytest.raises(BusinessException) as exc_info:
            await ask_question(db, "测试问题")
        assert exc_info.value.code == "QA_REQUIRES_API_PROVIDER"
        assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_qa_api_provider_unavailable(db):
    from app.core.qa_service import ask_question
    from app.core.exception_handlers import BusinessException

    provider = ExternalAPIProvider(api_key="", base_url="", model="gpt-4o-mini")
    with patch("app.core.qa_service.get_llm_provider", return_value=provider):
        with pytest.raises(BusinessException) as exc_info:
            await ask_question(db, "测试问题")
        assert exc_info.value.code == "API_PROVIDER_UNAVAILABLE"
        assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_qa_history_truncation(db):
    from app.core.qa_service import ask_question

    long_history = [{"role": "user", "content": f"问题{i}"} for i in range(20)]
    long_history.extend([{"role": "assistant", "content": f"回答{i}"} for i in range(20)])

    provider = ExternalAPIProvider(api_key="test", base_url="https://api.test.com/v1", model="gpt-4o-mini")
    mock_freeform = AsyncMock(return_value="测试回答")
    with patch.object(provider, "call_freeform", mock_freeform):
        with patch("app.core.qa_service.get_llm_provider", return_value=provider):
            with patch("app.core.qa_service.build_qa_context", return_value={"today": "2026-04-16"}):
                result = await ask_question(db, "新问题", long_history)

    assert result["answer"] == "测试回答"
    call_args = mock_freeform.call_args[0][0]
    user_msgs = [m for m in call_args if m["role"] == "user"]
    assert len(user_msgs) <= QA_MAX_HISTORY_TURNS + 1


@pytest.mark.asyncio
async def test_build_qa_context_no_db_writes(db):
    from app.core.qa_service import build_qa_context

    before = await db.execute(text("SELECT COUNT(*) FROM finance_records"))
    before_count = before.scalar() or 0

    try:
        await build_qa_context(db)
    except Exception:
        pass

    after = await db.execute(text("SELECT COUNT(*) FROM finance_records"))
    after_count = after.scalar() or 0
    assert after_count == before_count


@pytest.mark.asyncio
async def test_build_qa_context_with_related_records(db):
    from app.core.qa_service import build_qa_context
    from app.models.project import Milestone

    customer = Customer(name="测试客户", contact_person="张三", email="qa@example.com")
    db.add(customer)
    await db.flush()

    project = Project(
        name="进行中项目",
        customer_id=customer.id,
        status="in_progress",
        budget=120000,
    )
    db.add(project)
    await db.flush()

    milestone = Milestone(
        project_id=project.id,
        title="M1: 首付款",
        due_date=date(2026, 5, 1),
        payment_amount=60000,
        payment_status="unpaid",
        payment_due_date=date(2026, 5, 1),
    )
    db.add(milestone)

    contract = Contract(
        contract_no="HT-TEST-001",
        title="逾期合同",
        customer_id=customer.id,
        project_id=project.id,
        amount=80000,
        status="active",
        end_date=date(2026, 3, 1),
    )
    db.add(contract)
    await db.commit()

    context = await build_qa_context(db)

    assert context["active_projects"][0]["project_name"] == "进行中项目"
    assert context["active_projects"][0]["customer_name"] == "测试客户"
    assert context["active_projects"][0]["contract_amount"] == 120000.0
    assert context["active_projects"][0]["status"] == "in_progress"
    assert context["overdue_contracts"][0]["contract_title"] == "逾期合同"
    assert context["overdue_contracts"][0]["customer_name"] == "测试客户"
    assert "pending_payments" in context
    assert len(context["pending_payments"]) == 1
    assert context["pending_payments"][0]["project_name"] == "进行中项目"
    assert context["pending_payments"][0]["milestone_title"] == "M1: 首付款"
    assert context["pending_payments"][0]["payment_amount"] == 60000.0


@pytest.mark.asyncio
async def test_completed_project_with_pending_milestones_in_context(db):
    from app.core.qa_service import build_qa_context
    from app.models.project import Milestone

    customer = Customer(name="已完成客户", contact_person="李四", email="done@example.com")
    db.add(customer)
    await db.flush()

    project = Project(
        name="已完成项目",
        customer_id=customer.id,
        status="completed",
        budget=800000,
    )
    db.add(project)
    await db.flush()

    m1 = Milestone(
        project_id=project.id,
        title="M1: 需求确认",
        due_date=date(2026, 3, 16),
        payment_amount=240000,
        payment_status="unpaid",
        payment_due_date=date(2026, 3, 16),
    )
    m2 = Milestone(
        project_id=project.id,
        title="M2: 交付验收",
        due_date=date(2026, 4, 8),
        payment_amount=320000,
        payment_status="pending",
        payment_due_date=date(2026, 4, 8),
    )
    db.add_all([m1, m2])
    await db.commit()

    context = await build_qa_context(db)

    project_names = [p["project_name"] for p in context["active_projects"]]
    assert "已完成项目" in project_names

    pending = [p for p in context["pending_payments"] if p["project_name"] == "已完成项目"]
    assert len(pending) == 2
    assert pending[0]["payment_status"] == "unpaid"
    assert pending[1]["payment_status"] == "pending"


@pytest.mark.asyncio
async def test_qa_reads_agent_config_from_db(db):
    from app.core.qa_service import ask_question

    config_json = '{"provider":"api","api_key":"test-key","api_base":"https://api.test.com/v1","api_model":"gpt-4o-mini"}'
    db.add(
        SystemSetting(
            key="agent_config",
            value=config_json,
        )
    )
    await db.commit()

    provider = ExternalAPIProvider(api_key="test-key", base_url="https://api.test.com/v1", model="gpt-4o-mini")
    mock_freeform = AsyncMock(return_value="数据库配置生效")

    with patch.object(provider, "call_freeform", mock_freeform):
        with patch("app.core.qa_service.get_llm_provider", return_value=provider) as mock_get_provider:
            with patch("app.core.qa_service.build_qa_context", return_value={"today": "2026-04-16"}):
                result = await ask_question(db, "测试数据库配置")

    assert result["answer"] == "数据库配置生效"
    mock_get_provider.assert_called_once_with(json.loads(config_json))


@pytest.mark.asyncio
async def test_qa_empty_answer_raises_service_unavailable(db):
    from app.core.qa_service import ask_question
    from app.core.exception_handlers import BusinessException

    provider = ExternalAPIProvider(api_key="test", base_url="https://api.test.com/v1", model="gpt-4o-mini")

    with patch.object(provider, "call_freeform", AsyncMock(return_value=None)):
        with patch("app.core.qa_service.get_llm_provider", return_value=provider):
            with patch("app.core.qa_service.build_qa_context", return_value={"today": "2026-04-16"}):
                with pytest.raises(BusinessException) as exc_info:
                    await ask_question(db, "测试空回答")

    assert exc_info.value.code == "API_PROVIDER_UNAVAILABLE"
    assert exc_info.value.status_code == 503
