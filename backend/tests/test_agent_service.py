"""v2.0 AI Agent 闭环——Agent 运行 API 测试。"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from datetime import date, timedelta

from app.main import app
from app.database import get_db
from app.models.base import Base
from app.models.user import User
from app.models.customer import Customer
from app.models.project import Project, Task, Milestone
from app.models.agent_run import AgentRun
from app.models.agent_suggestion import AgentSuggestion
from app.core.security import get_password_hash

TEST_DB = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def db_session():
    engine = create_async_engine(TEST_DB, echo=False, poolclass=StaticPool)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        admin = User(
            username="admin", hashed_password=get_password_hash("admin123"),
            full_name="管理员", email="admin@test.com", is_active=True, is_superuser=True,
        )
        session.add(admin)
        await session.commit()
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    async def override():
        yield db_session
    app.dependency_overrides[get_db] = override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


async def _auth(client):
    r = await client.post("/api/v1/auth/login", data={"username": "admin", "password": "admin123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


class TestBusinessDecisionAgent:
    """经营决策 Agent 测试。"""

    async def test_run_returns_run_id(self, client):
        h = await _auth(client)
        r = await client.post("/api/v1/agents/business-decision/run", headers=h)
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == 0
        assert "run_id" in data["data"]
        assert data["data"]["status"] == "completed"

    async def test_run_records_agent_type(self, client):
        h = await _auth(client)
        r = await client.post("/api/v1/agents/business-decision/run", headers=h)
        assert r.json()["data"]["agent_type"] == "business_decision"


class TestProjectManagementAgent:
    """项目管理 Agent 测试。"""

    async def test_run_without_project_id(self, client):
        h = await _auth(client)
        r = await client.post("/api/v1/agents/project-management/run", headers=h)
        assert r.status_code == 200
        assert r.json()["data"]["status"] == "completed"

    async def test_run_with_project_id(self, client, db_session):
        c = Customer(name="测试客户")
        db_session.add(c)
        await db_session.commit()

        p = Project(name="测试项目", status="executing", customer_id=c.id)
        db_session.add(p)
        await db_session.commit()

        h = await _auth(client)
        r = await client.post(
            f"/api/v1/agents/project-management/run?project_id={p.id}", headers=h,
        )
        assert r.status_code == 200
        assert r.json()["data"]["status"] == "completed"


class TestAgentRunList:
    """运行记录列表测试。"""

    async def test_returns_empty_list(self, client):
        h = await _auth(client)
        r = await client.get("/api/v1/agents/runs", headers=h)
        assert r.status_code == 200
        assert r.json()["data"] == []

    async def test_returns_runs_after_execution(self, client):
        h = await _auth(client)
        await client.post("/api/v1/agents/business-decision/run", headers=h)
        r = await client.get("/api/v1/agents/runs", headers=h)
        assert len(r.json()["data"]) >= 1

    async def test_filter_by_status(self, client):
        h = await _auth(client)
        await client.post("/api/v1/agents/business-decision/run", headers=h)
        r = await client.get("/api/v1/agents/runs?status=completed", headers=h)
        assert all(item["status"] == "completed" for item in r.json()["data"])

    async def test_filter_by_agent_type(self, client):
        h = await _auth(client)
        await client.post("/api/v1/agents/business-decision/run", headers=h)
        await client.post("/api/v1/agents/project-management/run", headers=h)
        r = await client.get("/api/v1/agents/runs?agent_type=business_decision", headers=h)
        assert all(item["agent_type"] == "business_decision" for item in r.json()["data"])


class TestAgentRunDetail:
    """运行详情测试。"""

    async def test_returns_suggestions(self, client):
        h = await _auth(client)
        run_r = await client.post("/api/v1/agents/business-decision/run", headers=h)
        run_id = run_r.json()["data"]["run_id"]

        r = await client.get(f"/api/v1/agents/runs/{run_id}", headers=h)
        assert r.status_code == 200
        assert "suggestions" in r.json()["data"]

    async def test_not_found_returns_error(self, client):
        h = await _auth(client)
        r = await client.get("/api/v1/agents/runs/99999", headers=h)
        assert r.status_code == 400  # BusinessException returns 400


class TestPendingSuggestions:
    """待确认建议列表测试。"""

    async def test_returns_empty_initially(self, client):
        h = await _auth(client)
        r = await client.get("/api/v1/agents/suggestions/pending", headers=h)
        assert r.status_code == 200
        assert r.json()["data"] == []

    async def test_returns_suggestions_after_run(self, client):
        h = await _auth(client)
        await client.post("/api/v1/agents/business-decision/run", headers=h)
        r = await client.get("/api/v1/agents/suggestions/pending", headers=h)
        assert r.status_code == 200
        assert isinstance(r.json()["data"], list)

    async def test_filter_by_priority(self, client):
        h = await _auth(client)
        await client.post("/api/v1/agents/business-decision/run", headers=h)
        r = await client.get("/api/v1/agents/suggestions/pending?priority=high", headers=h)
        assert r.status_code == 200
        items = r.json()["data"]
        assert all(item["priority"] == "high" for item in items)
