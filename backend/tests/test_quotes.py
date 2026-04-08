"""v1.6 报价单 CRUD + 状态流转测试——FR-601"""
import pytest
import pytest_asyncio
from datetime import date, timedelta
from decimal import Decimal

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import get_db
from app.models.base import Base
from app.models.user import User
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


async def _auth(client: AsyncClient) -> dict:
    r = await client.post("/api/v1/auth/login", data={"username": "admin", "password": "admin123"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _create_customer(client: AsyncClient, h: dict) -> int:
    resp = await client.post("/api/v1/customers", json={
        "name": "测试客户",
        "contact_person": "张三",
        "phone": "13800138000",
    }, headers=h)
    assert resp.status_code == 201
    return resp.json()["id"]


async def _create_quote(client: AsyncClient, h: dict, customer_id: int, **overrides) -> dict:
    payload = {
        "title": "测试报价",
        "customer_id": customer_id,
        "requirement_summary": "测试需求摘要",
        "estimate_days": 30,
        "daily_rate": "1000.00",
        "valid_until": str(date.today() + timedelta(days=30)),
    }
    payload.update(overrides)
    resp = await client.post("/api/v1/quotations", json=payload, headers=h)
    assert resp.status_code == 201, f"创建报价单失败: {resp.text}"
    return resp.json()


class TestQuoteCRUD:
    """FR-601: 报价单 CRUD 测试。"""

    @pytest.mark.asyncio
    async def test_create_quote_auto_generates_no(self, client: AsyncClient):
        h = await _auth(client)
        cid = await _create_customer(client, h)
        q = await _create_quote(client, h, cid)
        assert q["quote_no"].startswith("BJ-")
        assert len(q["quote_no"].split("-")) == 3

    @pytest.mark.asyncio
    async def test_quote_no_format_correct(self, client: AsyncClient):
        h = await _auth(client)
        cid = await _create_customer(client, h)
        q = await _create_quote(client, h, cid)
        parts = q["quote_no"].split("-")
        assert parts[0] == "BJ"
        assert len(parts[1]) == 8
        assert len(parts[2]) == 3

    @pytest.mark.asyncio
    async def test_create_quote_default_status_draft(self, client: AsyncClient):
        h = await _auth(client)
        cid = await _create_customer(client, h)
        q = await _create_quote(client, h, cid)
        assert q["status"] == "draft"

    @pytest.mark.asyncio
    async def test_get_quotes_ordered_by_created_desc(self, client: AsyncClient):
        h = await _auth(client)
        cid = await _create_customer(client, h)
        q1 = await _create_quote(client, h, cid, title="报价1")
        q2 = await _create_quote(client, h, cid, title="报价2")
        resp = await client.get("/api/v1/quotations", headers=h)
        items = resp.json()["items"]
        assert items[0]["id"] == q2["id"]

    @pytest.mark.asyncio
    async def test_get_quote_detail_success(self, client: AsyncClient):
        h = await _auth(client)
        cid = await _create_customer(client, h)
        q = await _create_quote(client, h, cid)
        resp = await client.get(f"/api/v1/quotations/{q['id']}", headers=h)
        assert resp.status_code == 200
        assert resp.json()["quote_no"] == q["quote_no"]

    @pytest.mark.asyncio
    async def test_update_draft_quote_success(self, client: AsyncClient):
        h = await _auth(client)
        cid = await _create_customer(client, h)
        q = await _create_quote(client, h, cid)
        resp = await client.put(f"/api/v1/quotations/{q['id']}", json={
            "title": "更新标题",
        }, headers=h)
        assert resp.status_code == 200
        assert resp.json()["title"] == "更新标题"

    @pytest.mark.asyncio
    async def test_update_accepted_quote_core_fields_rejected(self, client: AsyncClient):
        h = await _auth(client)
        cid = await _create_customer(client, h)
        q = await _create_quote(client, h, cid)
        await client.post(f"/api/v1/quotations/{q['id']}/send", headers=h)
        await client.post(f"/api/v1/quotations/{q['id']}/accept", headers=h)
        resp = await client.put(f"/api/v1/quotations/{q['id']}", json={
            "title": "尝试修改",
        }, headers=h)
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_update_accepted_quote_notes_allowed(self, client: AsyncClient):
        h = await _auth(client)
        cid = await _create_customer(client, h)
        q = await _create_quote(client, h, cid)
        await client.post(f"/api/v1/quotations/{q['id']}/send", headers=h)
        await client.post(f"/api/v1/quotations/{q['id']}/accept", headers=h)
        resp = await client.put(f"/api/v1/quotations/{q['id']}", json={
            "notes": "更新备注",
        }, headers=h)
        assert resp.status_code == 200
        assert resp.json()["notes"] == "更新备注"

    @pytest.mark.asyncio
    async def test_delete_draft_quote_success(self, client: AsyncClient):
        h = await _auth(client)
        cid = await _create_customer(client, h)
        q = await _create_quote(client, h, cid)
        resp = await client.delete(f"/api/v1/quotations/{q['id']}", headers=h)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_sent_quote_rejected(self, client: AsyncClient):
        h = await _auth(client)
        cid = await _create_customer(client, h)
        q = await _create_quote(client, h, cid)
        await client.post(f"/api/v1/quotations/{q['id']}/send", headers=h)
        resp = await client.delete(f"/api/v1/quotations/{q['id']}", headers=h)
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_delete_accepted_quote_rejected(self, client: AsyncClient):
        h = await _auth(client)
        cid = await _create_customer(client, h)
        q = await _create_quote(client, h, cid)
        await client.post(f"/api/v1/quotations/{q['id']}/send", headers=h)
        await client.post(f"/api/v1/quotations/{q['id']}/accept", headers=h)
        resp = await client.delete(f"/api/v1/quotations/{q['id']}", headers=h)
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_customer_not_found_returns_error(self, client: AsyncClient):
        h = await _auth(client)
        resp = await client.post("/api/v1/quotations", json={
            "title": "测试",
            "customer_id": 99999,
            "requirement_summary": "测试",
            "estimate_days": 10,
            "valid_until": str(date.today() + timedelta(days=30)),
        }, headers=h)
        assert resp.status_code in (400, 404, 500)

    @pytest.mark.asyncio
    async def test_status_transition_illegal_returns_422(self, client: AsyncClient):
        h = await _auth(client)
        cid = await _create_customer(client, h)
        q = await _create_quote(client, h, cid)
        resp = await client.post(f"/api/v1/quotations/{q['id']}/reject", headers=h)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_cancelled_quote_cannot_be_accepted(self, client: AsyncClient):
        h = await _auth(client)
        cid = await _create_customer(client, h)
        q = await _create_quote(client, h, cid)
        await client.post(f"/api/v1/quotations/{q['id']}/cancel", headers=h)
        resp = await client.post(f"/api/v1/quotations/{q['id']}/accept", headers=h)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_send_sets_sent_at(self, client: AsyncClient):
        h = await _auth(client)
        cid = await _create_customer(client, h)
        q = await _create_quote(client, h, cid)
        resp = await client.post(f"/api/v1/quotations/{q['id']}/send", headers=h)
        assert resp.status_code == 200
        assert resp.json()["sent_at"] is not None

    @pytest.mark.asyncio
    async def test_accept_sets_accepted_at(self, client: AsyncClient):
        h = await _auth(client)
        cid = await _create_customer(client, h)
        q = await _create_quote(client, h, cid)
        await client.post(f"/api/v1/quotations/{q['id']}/send", headers=h)
        resp = await client.post(f"/api/v1/quotations/{q['id']}/accept", headers=h)
        assert resp.status_code == 200
        assert resp.json()["accepted_at"] is not None

    @pytest.mark.asyncio
    async def test_quote_not_found_returns_404(self, client: AsyncClient):
        h = await _auth(client)
        resp = await client.get("/api/v1/quotations/99999", headers=h)
        assert resp.status_code == 404
