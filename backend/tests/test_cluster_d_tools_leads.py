"""Cluster D Phase 1 — 工具入口台账 + 客户线索台账测试（Red 阶段）。

7 个测试用例，对应 PRD FR-D-001 ~ FR-D-007。
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import get_db
from app.models.base import Base
from app.models.user import User
from app.core.security import get_password_hash


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def db_session():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=StaticPool)
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
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


async def _login(client: AsyncClient) -> dict:
    r = await client.post("/api/v1/auth/login", data={"username": "admin", "password": "admin123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


class TestToolEntryCRUD:
    """FR-D-001: 工具入口台账 CRUD"""

    @pytest.mark.asyncio
    async def test_tool_entry_create_and_list(self, client: AsyncClient, db_session: AsyncSession):
        headers = await _login(client)

        create_resp = await client.post(
            "/api/v1/tool-entries",
            json={"action_name": "数据标注", "tool_name": "Label Studio"},
            headers=headers,
        )
        assert create_resp.status_code in [200, 201]
        assert create_resp.json()["status"] == "pending"

        list_resp = await client.get("/api/v1/tool-entries", headers=headers)
        assert list_resp.status_code == 200
        data = list_resp.json()
        assert data["total"] >= 1


class TestToolEntryStatusTransition:
    """FR-D-002: 工具入口台账状态流转"""

    @pytest.mark.asyncio
    async def test_tool_entry_valid_transition(self, client: AsyncClient, db_session: AsyncSession):
        headers = await _login(client)

        create_resp = await client.post(
            "/api/v1/tool-entries",
            json={"action_name": "模型训练", "tool_name": "PyTorch"},
            headers=headers,
        )
        entry_id = create_resp.json()["id"]

        update_resp = await client.patch(
            f"/api/v1/tool-entries/{entry_id}/status",
            json={"status": "in_progress"},
            headers=headers,
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["status"] == "in_progress"

    @pytest.mark.asyncio
    async def test_tool_entry_invalid_transition(self, client: AsyncClient, db_session: AsyncSession):
        headers = await _login(client)

        create_resp = await client.post(
            "/api/v1/tool-entries",
            json={"action_name": "数据清洗", "tool_name": "Pandas"},
            headers=headers,
        )
        entry_id = create_resp.json()["id"]

        update_resp = await client.patch(
            f"/api/v1/tool-entries/{entry_id}/status",
            json={"status": "backfilled"},
            headers=headers,
        )
        assert update_resp.status_code == 400


class TestToolEntryDelete:
    """FR-D-003: 工具入口台账删除"""

    @pytest.mark.asyncio
    async def test_tool_entry_delete(self, client: AsyncClient, db_session: AsyncSession):
        headers = await _login(client)

        create_resp = await client.post(
            "/api/v1/tool-entries",
            json={"action_name": "测试动作", "tool_name": "测试工具"},
            headers=headers,
        )
        entry_id = create_resp.json()["id"]

        delete_resp = await client.delete(f"/api/v1/tool-entries/{entry_id}", headers=headers)
        assert delete_resp.status_code == 200
        assert delete_resp.json()["deleted"] is True


class TestLeadCRUD:
    """FR-D-004: 客户线索台账 CRUD"""

    @pytest.mark.asyncio
    async def test_lead_create_and_list(self, client: AsyncClient, db_session: AsyncSession):
        headers = await _login(client)

        create_resp = await client.post(
            "/api/v1/leads",
            json={"source": "referral", "status": "initial_contact", "next_action": "电话沟通"},
            headers=headers,
        )
        assert create_resp.status_code in [200, 201]

        list_resp = await client.get("/api/v1/leads", headers=headers)
        assert list_resp.status_code == 200
        data = list_resp.json()
        assert data["total"] >= 1


class TestLeadStatusTransition:
    """FR-D-005: 客户线索台账状态流转"""

    @pytest.mark.asyncio
    async def test_lead_valid_transition(self, client: AsyncClient, db_session: AsyncSession):
        headers = await _login(client)

        create_resp = await client.post(
            "/api/v1/leads",
            json={"source": "website", "status": "initial_contact", "next_action": "邮件联系"},
            headers=headers,
        )
        lead_id = create_resp.json()["id"]

        update_resp = await client.put(
            f"/api/v1/leads/{lead_id}",
            json={"status": "intent_confirmed"},
            headers=headers,
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["status"] == "intent_confirmed"

    @pytest.mark.asyncio
    async def test_lead_invalid_transition(self, client: AsyncClient, db_session: AsyncSession):
        headers = await _login(client)

        create_resp = await client.post(
            "/api/v1/leads",
            json={"source": "event", "status": "initial_contact"},
            headers=headers,
        )
        lead_id = create_resp.json()["id"]

        update_resp = await client.put(
            f"/api/v1/leads/{lead_id}",
            json={"status": "converted"},
            headers=headers,
        )
        assert update_resp.status_code == 400


class TestLeadDelete:
    """FR-D-006: 客户线索台账删除"""

    @pytest.mark.asyncio
    async def test_lead_delete(self, client: AsyncClient, db_session: AsyncSession):
        headers = await _login(client)

        create_resp = await client.post(
            "/api/v1/leads",
            json={"source": "cold_outreach", "status": "initial_contact"},
            headers=headers,
        )
        lead_id = create_resp.json()["id"]

        delete_resp = await client.delete(f"/api/v1/leads/{lead_id}", headers=headers)
        assert delete_resp.status_code == 200
        assert delete_resp.json()["deleted"] is True


class TestLeadConvertWithClientId:
    """FR-D-007: 线索转化时关联 client_id"""

    @pytest.mark.asyncio
    async def test_lead_convert_with_client_id(self, client: AsyncClient, db_session: AsyncSession):
        headers = await _login(client)

        create_resp = await client.post(
            "/api/v1/leads",
            json={"source": "referral", "status": "initial_contact"},
            headers=headers,
        )
        lead_id = create_resp.json()["id"]

        await client.put(
            f"/api/v1/leads/{lead_id}",
            json={"status": "intent_confirmed"},
            headers=headers,
        )

        convert_resp = await client.put(
            f"/api/v1/leads/{lead_id}",
            json={"status": "converted", "client_id": 1},
            headers=headers,
        )
        assert convert_resp.status_code == 200
        assert convert_resp.json()["status"] == "converted"
        assert convert_resp.json()["client_id"] == 1
