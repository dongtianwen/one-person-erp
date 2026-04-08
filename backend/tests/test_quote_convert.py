"""v1.6 报价转合同测试——FR-603"""
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
        "name": "转合同测试客户",
        "contact_person": "张三",
        "phone": "13800138000",
    }, headers=h)
    return resp.json()["id"]


async def _create_and_accept_quote(client: AsyncClient, h: dict, customer_id: int) -> dict:
    resp = await client.post("/api/v1/quotations", json={
        "title": "转合同报价",
        "customer_id": customer_id,
        "requirement_summary": "需求摘要",
        "estimate_days": 30,
        "daily_rate": "1000.00",
        "valid_until": str(date.today() + timedelta(days=30)),
    }, headers=h)
    q = resp.json()
    await client.post(f"/api/v1/quotations/{q['id']}/send", headers=h)
    await client.post(f"/api/v1/quotations/{q['id']}/accept", headers=h)
    resp = await client.get(f"/api/v1/quotations/{q['id']}", headers=h)
    return resp.json()


class TestQuoteConvert:
    """FR-603: 报价转合同测试。"""

    @pytest.mark.asyncio
    async def test_convert_accepted_quote_to_contract_success(self, client: AsyncClient):
        h = await _auth(client)
        cid = await _create_customer(client, h)
        q = await _create_and_accept_quote(client, h, cid)
        resp = await client.post(f"/api/v1/quotations/{q['id']}/convert-to-contract", headers=h)
        assert resp.status_code == 200
        assert resp.json()["converted_contract_id"] is not None

    @pytest.mark.asyncio
    async def test_convert_only_accepted_allowed(self, client: AsyncClient):
        h = await _auth(client)
        cid = await _create_customer(client, h)
        resp = await client.post("/api/v1/quotations", json={
            "title": "测试", "customer_id": cid,
            "requirement_summary": "需求", "estimate_days": 10,
            "valid_until": str(date.today() + timedelta(days=30)),
        }, headers=h)
        q = resp.json()
        resp = await client.post(f"/api/v1/quotations/{q['id']}/convert-to-contract", headers=h)
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_convert_quote_only_once(self, client: AsyncClient):
        h = await _auth(client)
        cid = await _create_customer(client, h)
        q = await _create_and_accept_quote(client, h, cid)
        await client.post(f"/api/v1/quotations/{q['id']}/convert-to-contract", headers=h)
        resp = await client.post(f"/api/v1/quotations/{q['id']}/convert-to-contract", headers=h)
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_convert_sets_converted_contract_id(self, client: AsyncClient):
        h = await _auth(client)
        cid = await _create_customer(client, h)
        q = await _create_and_accept_quote(client, h, cid)
        resp = await client.post(f"/api/v1/quotations/{q['id']}/convert-to-contract", headers=h)
        assert resp.json()["converted_contract_id"] is not None

    @pytest.mark.asyncio
    async def test_contract_created_from_quote_fields_copied(self, client: AsyncClient):
        h = await _auth(client)
        cid = await _create_customer(client, h)
        q = await _create_and_accept_quote(client, h, cid)
        resp = await client.post(f"/api/v1/quotations/{q['id']}/convert-to-contract", headers=h)
        contract_id = resp.json()["converted_contract_id"]
        cresp = await client.get(f"/api/v1/contracts/{contract_id}", headers=h)
        contract = cresp.json()
        assert contract["title"] == q["title"]
        assert contract["customer_id"] == q["customer_id"]
        assert contract["status"] == "draft"

    @pytest.mark.asyncio
    async def test_quote_not_found_returns_404(self, client: AsyncClient):
        h = await _auth(client)
        resp = await client.post("/api/v1/quotations/99999/convert-to-contract", headers=h)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_contract_quotation_id_set(self, client: AsyncClient):
        h = await _auth(client)
        cid = await _create_customer(client, h)
        q = await _create_and_accept_quote(client, h, cid)
        resp = await client.post(f"/api/v1/quotations/{q['id']}/convert-to-contract", headers=h)
        contract_id = resp.json()["converted_contract_id"]
        cresp = await client.get(f"/api/v1/contracts/{contract_id}", headers=h)
        contract = cresp.json()
        assert contract.get("quotation_id") == q["id"]
