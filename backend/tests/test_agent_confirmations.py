"""v2.0 AI Agent 闭环——建议确认与动作执行 API 测试。"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import select

from app.main import app
from app.database import get_db
from app.models.base import Base
from app.models.user import User
from app.models.agent_run import AgentRun
from app.models.agent_suggestion import AgentSuggestion
from app.models.agent_action import AgentAction
from app.models.human_confirmation import HumanConfirmation
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


async def _create_pending_suggestion(db_session, action_type="create_todo"):
    run = AgentRun(agent_type="business_decision", trigger_type="manual", status="completed")
    db_session.add(run)
    await db_session.commit()

    suggestion = AgentSuggestion(
        agent_run_id=run.id,
        decision_type="overdue_payment",
        suggestion_type="overdue_payment",
        title="测试建议",
        description="测试描述",
        priority="high",
        status="pending",
        suggested_action=action_type,
    )
    db_session.add(suggestion)
    await db_session.commit()
    await db_session.refresh(suggestion)
    return suggestion


class TestConfirmSuggestion:
    """建议确认测试。"""

    async def test_accept_creates_action(self, client, db_session):
        sug = await _create_pending_suggestion(db_session, action_type="create_todo")
        h = await _auth(client)
        r = await client.post(
            f"/api/v1/agents/suggestions/{sug.id}/confirm",
            headers=h,
            json={"decision_type": "accepted"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == 0
        assert data["data"]["decision_type"] == "accepted"
        assert data["data"]["action"] is not None

    async def test_reject_no_action(self, client, db_session):
        sug = await _create_pending_suggestion(db_session)
        h = await _auth(client)
        r = await client.post(
            f"/api/v1/agents/suggestions/{sug.id}/confirm",
            headers=h,
            json={"decision_type": "rejected"},
        )
        assert r.status_code == 200
        assert r.json()["data"]["action"] is None

    async def test_not_found(self, client):
        h = await _auth(client)
        r = await client.post(
            "/api/v1/agents/suggestions/99999/confirm",
            headers=h,
            json={"decision_type": "accepted"},
        )
        assert r.status_code == 400

    async def test_already_confirmed(self, client, db_session):
        sug = await _create_pending_suggestion(db_session)
        sug.status = "confirmed"
        await db_session.commit()

        h = await _auth(client)
        r = await client.post(
            f"/api/v1/agents/suggestions/{sug.id}/confirm",
            headers=h,
            json={"decision_type": "accepted"},
        )
        assert r.status_code == 400

    async def test_with_reason_fields(self, client, db_session):
        sug = await _create_pending_suggestion(db_session)
        h = await _auth(client)
        r = await client.post(
            f"/api/v1/agents/suggestions/{sug.id}/confirm",
            headers=h,
            json={
                "decision_type": "accepted",
                "reason_code": "confirmed",
                "free_text_reason": "同意执行",
                "corrected_fields": {"priority": "high"},
                "user_priority_override": "high",
            },
        )
        assert r.status_code == 200
        assert r.json()["data"]["decision_type"] == "accepted"

    async def test_confirms_saves_confirmation_record(self, client, db_session):
        sug = await _create_pending_suggestion(db_session)
        h = await _auth(client)
        await client.post(
            f"/api/v1/agents/suggestions/{sug.id}/confirm",
            headers=h,
            json={"decision_type": "accepted", "free_text_reason": "test reason"},
        )
        result = await db_session.execute(
            select(HumanConfirmation).where(HumanConfirmation.suggestion_id == sug.id)
        )
        confirmations = result.scalars().all()
        assert len(confirmations) == 1
        assert confirmations[0].free_text_reason == "test reason"


class TestActionExecution:
    """动作执行测试。"""

    async def test_create_todo_action(self, client, db_session):
        sug = await _create_pending_suggestion(db_session, action_type="create_todo")
        h = await _auth(client)
        r = await client.post(
            f"/api/v1/agents/suggestions/{sug.id}/confirm",
            headers=h,
            json={"decision_type": "accepted"},
        )
        assert r.status_code == 200
        action_id = r.json()["data"]["action"]["action_id"]
        assert action_id is not None

    async def test_create_reminder_action(self, client, db_session):
        sug = await _create_pending_suggestion(db_session, action_type="create_reminder")
        h = await _auth(client)
        r = await client.post(
            f"/api/v1/agents/suggestions/{sug.id}/confirm",
            headers=h,
            json={"decision_type": "accepted"},
        )
        assert r.status_code == 200
        assert r.json()["data"]["action"]["status"] == "executed"

    async def test_generate_report_action(self, client, db_session):
        sug = await _create_pending_suggestion(db_session, action_type="generate_report")
        h = await _auth(client)
        r = await client.post(
            f"/api/v1/agents/suggestions/{sug.id}/confirm",
            headers=h,
            json={"decision_type": "accepted"},
        )
        assert r.status_code == 200
        assert r.json()["data"]["action"]["status"] == "executed"

    async def test_none_action(self, client, db_session):
        sug = await _create_pending_suggestion(db_session, action_type="none")
        h = await _auth(client)
        r = await client.post(
            f"/api/v1/agents/suggestions/{sug.id}/confirm",
            headers=h,
            json={"decision_type": "accepted"},
        )
        assert r.status_code == 200
        assert r.json()["data"]["action"]["status"] == "executed"


class TestActionListAndDetail:
    """动作列表和详情测试。"""

    async def test_list_actions_empty(self, client):
        h = await _auth(client)
        r = await client.get("/api/v1/agents/actions", headers=h)
        assert r.status_code == 200
        assert r.json()["data"] == []

    async def test_list_actions_after_confirm(self, client, db_session):
        sug = await _create_pending_suggestion(db_session, action_type="create_todo")
        h = await _auth(client)
        await client.post(
            f"/api/v1/agents/suggestions/{sug.id}/confirm",
            headers=h,
            json={"decision_type": "accepted"},
        )
        r = await client.get("/api/v1/agents/actions", headers=h)
        assert len(r.json()["data"]) >= 1

    async def test_get_action_detail(self, client, db_session):
        sug = await _create_pending_suggestion(db_session, action_type="create_todo")
        h = await _auth(client)
        confirm_r = await client.post(
            f"/api/v1/agents/suggestions/{sug.id}/confirm",
            headers=h,
            json={"decision_type": "accepted"},
        )
        action_id = confirm_r.json()["data"]["action"]["action_id"]

        r = await client.get(f"/api/v1/agents/actions/{action_id}", headers=h)
        assert r.status_code == 200
        assert r.json()["data"]["id"] == action_id

    async def test_get_action_not_found(self, client):
        h = await _auth(client)
        r = await client.get("/api/v1/agents/actions/99999", headers=h)
        assert r.status_code == 400

    async def test_filter_actions_by_status(self, client, db_session):
        sug = await _create_pending_suggestion(db_session, action_type="create_todo")
        h = await _auth(client)
        await client.post(
            f"/api/v1/agents/suggestions/{sug.id}/confirm",
            headers=h,
            json={"decision_type": "accepted"},
        )
        r = await client.get("/api/v1/agents/actions?status=executed", headers=h)
        assert all(item["status"] == "executed" for item in r.json()["data"])
