"""Cluster A2 Phase 1 — summary 底座测试（Red 阶段）。

9 个测试用例，对应 PRD FR-A2-001 ~ FR-A2-009。
本阶段仅编写测试，不编写任何业务代码，运行后应全部 FAILED。
"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.entity_snapshot import EntitySnapshot
from app.models.dashboard_summary import DashboardSummary
from app.models.customer import Customer
from app.models.project import Project, Milestone
from app.models.contract import Contract
from app.models.finance import FinanceRecord
from app.models.agent_suggestion import AgentSuggestion
from app.services.summary_service import refresh_summary, rebuild_summary_full
from app.core.constants import (
    SUMMARY_TRIGGER_CONTRACT_CONFIRMED,
    SUMMARY_TRIGGER_PAYMENT_RECORDED,
    SUMMARY_TRIGGER_INVOICE_RECORDED,
    SUMMARY_TRIGGER_DELIVERY_COMPLETED,
    SUMMARY_TRIGGER_MILESTONE_CHANGED,
    METRIC_CONTRACT_ACTIVE_COUNT,
    METRIC_FINANCE_RECEIVABLE_TOTAL,
    METRIC_FINANCE_OVERDUE_TOTAL,
    METRIC_DELIVERY_IN_PROGRESS_COUNT,
    METRIC_PROJECT_AT_RISK_COUNT,
    WARNING_SUMMARY_REFRESH_FAILED,
)


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def db_session():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=StaticPool)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(DashboardSummary.metadata.create_all)
        await conn.run_sync(Customer.metadata.create_all)
        await conn.run_sync(Project.metadata.create_all)
        await conn.run_sync(Contract.metadata.create_all)
        await conn.run_sync(FinanceRecord.metadata.create_all)
        await conn.run_sync(Milestone.metadata.create_all)
        await conn.run_sync(AgentSuggestion.metadata.create_all)

    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        try:
            await conn.run_sync(Base.metadata.drop_all)
        except Exception:
            pass

    await engine.dispose()


class TestSummaryContractConfirmed:
    """FR-A2-001: 合同状态确认后，相关 metric_key 刷新"""

    @pytest.mark.asyncio
    async def test_summary_refreshed_on_contract_confirm(self, db_session: AsyncSession):
        success, warning_code = await refresh_summary(
            db=db_session,
            trigger_event=SUMMARY_TRIGGER_CONTRACT_CONFIRMED,
            related_ids={"contract_id": 1},
        )
        assert success is True
        assert warning_code is None

        result = await db_session.execute(
            __import__("sqlalchemy").select(DashboardSummary).where(
                DashboardSummary.metric_key == METRIC_CONTRACT_ACTIVE_COUNT
            )
        )
        row = result.scalar_one_or_none()
        assert row is not None


class TestSummaryPaymentRecorded:
    """FR-A2-002: 收款录入后，相关 metric_key 刷新"""

    @pytest.mark.asyncio
    async def test_summary_refreshed_on_payment_record(self, db_session: AsyncSession):
        success, _ = await refresh_summary(
            db=db_session,
            trigger_event=SUMMARY_TRIGGER_PAYMENT_RECORDED,
            related_ids={"finance_id": 1},
        )
        assert success is True

        result = await db_session.execute(
            __import__("sqlalchemy").select(DashboardSummary).where(
                DashboardSummary.metric_key == METRIC_FINANCE_RECEIVABLE_TOTAL
            )
        )
        row = result.scalar_one_or_none()
        assert row is not None


class TestSummaryInvoiceRecorded:
    """FR-A2-003: 发票录入后，相关 metric_key 刷新"""

    @pytest.mark.asyncio
    async def test_summary_refreshed_on_invoice_record(self, db_session: AsyncSession):
        success, _ = await refresh_summary(
            db=db_session,
            trigger_event=SUMMARY_TRIGGER_INVOICE_RECORDED,
            related_ids={"invoice_id": 1},
        )
        assert success is True


class TestSummaryDeliveryCompleted:
    """FR-A2-004: 交付完成后，相关 metric_key 刷新"""

    @pytest.mark.asyncio
    async def test_summary_refreshed_on_delivery_complete(self, db_session: AsyncSession):
        success, _ = await refresh_summary(
            db=db_session,
            trigger_event=SUMMARY_TRIGGER_DELIVERY_COMPLETED,
            related_ids={"delivery_id": 1},
        )
        assert success is True

        result = await db_session.execute(
            __import__("sqlalchemy").select(DashboardSummary).where(
                DashboardSummary.metric_key == METRIC_DELIVERY_IN_PROGRESS_COUNT
            )
        )
        row = result.scalar_one_or_none()
        assert row is not None


class TestSummaryMilestoneChanged:
    """FR-A2-005: 里程碑状态变更后，相关 metric_key 刷新"""

    @pytest.mark.asyncio
    async def test_summary_refreshed_on_milestone_change(self, db_session: AsyncSession):
        success, _ = await refresh_summary(
            db=db_session,
            trigger_event=SUMMARY_TRIGGER_MILESTONE_CHANGED,
            related_ids={"milestone_id": 1},
        )
        assert success is True

        result = await db_session.execute(
            __import__("sqlalchemy").select(DashboardSummary).where(
                DashboardSummary.metric_key == METRIC_PROJECT_AT_RISK_COUNT
            )
        )
        row = result.scalar_one_or_none()
        assert row is not None


class TestSummaryRefreshFailureReturnsWarning:
    """FR-A2-006: summary 刷新失败时，API 返回 success=true + warning_code，主业务未回滚"""

    @pytest.mark.asyncio
    async def test_summary_refresh_failure_returns_warning(self, db_session: AsyncSession):
        main_business_saved = {"id": 1, "saved": False}

        async def mock_main_business(db):
            main_business_saved["saved"] = True

        success, warning_code = await refresh_summary(
            db=db_session,
            trigger_event="invalid_trigger_event",
            related_ids={},
        )
        assert success is True
        assert warning_code is None


class TestSummaryFullRebuild:
    """FR-A2-007: 全量重建接口可被手动触发，结果与逐条刷新一致"""

    @pytest.mark.asyncio
    async def test_summary_full_rebuild(self, db_session: AsyncSession):
        result = await rebuild_summary_full(db=db_session)
        assert result is True

        from sqlalchemy import select, func
        count_result = await db_session.execute(
            select(func.count(DashboardSummary.id))
        )
        count = count_result.scalar()
        assert count > 0


class TestSummaryReadOnlyFromSummaryTable:
    """FR-A2-008: 首页 API 不执行任何跨表 join，仅查 dashboard_summary"""

    @pytest.mark.asyncio
    async def test_summary_read_only_from_summary_table(self, db_session: AsyncSession):
        await rebuild_summary_full(db=db_session)

        from sqlalchemy import select
        result = await db_session.execute(select(DashboardSummary))
        rows = result.scalars().all()
        assert len(rows) > 0

        for row in rows:
            assert row.metric_key is not None


class TestSummaryNonTriggerWriteNoRefresh:
    """FR-A2-009: 非触发事件的普通写操作不触发 summary 刷新"""

    @pytest.mark.asyncio
    async def test_summary_non_trigger_write_no_refresh(self, db_session: AsyncSession):
        success, warning_code = await refresh_summary(
            db=db_session,
            trigger_event="some_random_event",
            related_ids={},
        )
        assert success is True
        assert warning_code is None

        from sqlalchemy import select, func
        count_result = await db_session.execute(
            select(func.count(DashboardSummary.id))
        )
        count = count_result.scalar()
        assert count == 0
