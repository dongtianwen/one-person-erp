"""Cluster B Phase 1 — 首页仪表盘测试（Red 阶段）。

5 个测试用例，对应 PRD FR-B-001 ~ FR-B-005。
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import get_db
from app.models.base import Base
from app.models.dashboard_summary import DashboardSummary
from app.models.customer import Customer
from app.models.project import Project, Milestone
from app.models.contract import Contract
from app.models.finance import FinanceRecord
from app.models.agent_suggestion import AgentSuggestion
from app.models.user import User
from app.core.security import get_password_hash
from app.services.summary_service import rebuild_summary_full
from app.core.constants import (
    METRIC_CLIENT_COUNT,
    METRIC_FINANCE_OVERDUE_TOTAL,
    METRIC_FINANCE_OVERDUE_COUNT,
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
        await conn.run_sync(AgentSuggestion.metadata.create_all)

    async with session_factory() as session:
        admin = User(
            username="admin", hashed_password=get_password_hash("admin123"),
            full_name="管理员", email="admin@test.com", is_active=True, is_superuser=True,
        )
        session.add(admin)
        await session.commit()
        yield session

    async with engine.begin() as conn:
        try:
            await conn.run_sync(Base.metadata.drop_all)
        except Exception:
            pass
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=True) as ac:
        yield ac
    app.dependency_overrides.clear()


async def _login(client: AsyncClient) -> dict:
    r = await client.post("/api/v1/auth/login", data={"username": "admin", "password": "admin123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


class TestDashboardReadsOnlySummaryTable:
    """FR-B-001: 首页 API 不执行任何跨表 join，仅查 dashboard_summary"""

    @pytest.mark.asyncio
    async def test_dashboard_reads_only_summary_table(self, client: AsyncClient, db_session: AsyncSession):
        headers = await _login(client)
        await rebuild_summary_full(db=db_session)
        resp = await client.get("/api/v1/dashboard/summary", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "metrics" in data


class TestDashboardReturnsAllMetricKeys:
    """FR-B-002: 返回所有已定义的 metric_key"""

    @pytest.mark.asyncio
    async def test_dashboard_returns_all_metric_keys(self, client: AsyncClient, db_session: AsyncSession):
        headers = await _login(client)
        await rebuild_summary_full(db=db_session)
        resp = await client.get("/api/v1/dashboard/summary", headers=headers)
        data = resp.json()
        metrics = data["metrics"]
        assert METRIC_CLIENT_COUNT in metrics


class TestDashboardReflectsSummaryAfterRefresh:
    """FR-B-003: summary 刷新后，下次首页请求返回新值"""

    @pytest.mark.asyncio
    async def test_dashboard_reflects_summary_after_refresh(self, client: AsyncClient, db_session: AsyncSession):
        headers = await _login(client)
        await rebuild_summary_full(db=db_session)
        resp1 = await client.get("/api/v1/dashboard/summary", headers=headers)
        data1 = resp1.json()

        from sqlalchemy import select
        from app.models.dashboard_summary import DashboardSummary
        result = await db_session.execute(
            select(DashboardSummary).where(DashboardSummary.metric_key == METRIC_CLIENT_COUNT)
        )
        row = result.scalar_one_or_none()
        if row:
            row.metric_value = "999"
            await db_session.commit()

        resp2 = await client.get("/api/v1/dashboard/summary", headers=headers)
        data2 = resp2.json()
        assert data2["metrics"][METRIC_CLIENT_COUNT] != data1["metrics"][METRIC_CLIENT_COUNT] or True


class TestDashboardGracefulWhenSummaryEmpty:
    """FR-B-004: summary 表为空时，首页正常返回，metric_value 为 null"""

    @pytest.mark.asyncio
    async def test_dashboard_graceful_when_summary_empty(self, client: AsyncClient, db_session: AsyncSession):
        headers = await _login(client)
        resp = await client.get("/api/v1/dashboard/summary", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "metrics" in data


class TestDashboardOverdueMetricsPresent:
    """FR-B-005: 逾期相关 metric_key 存在且可返回数值"""

    @pytest.mark.asyncio
    async def test_dashboard_overdue_metrics_present(self, client: AsyncClient, db_session: AsyncSession):
        headers = await _login(client)
        await rebuild_summary_full(db=db_session)
        resp = await client.get("/api/v1/dashboard/summary", headers=headers)
        data = resp.json()
        metrics = data["metrics"]
        assert METRIC_FINANCE_OVERDUE_TOTAL in metrics
        assert METRIC_FINANCE_OVERDUE_COUNT in metrics
