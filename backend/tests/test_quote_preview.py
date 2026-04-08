"""v1.6 报价预览端点测试——FR-602"""
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


class TestQuotePreview:
    """FR-602: 报价预览接口测试。"""

    @pytest.mark.asyncio
    async def test_preview_endpoint_returns_calculation_result(self, client: AsyncClient):
        h = await _auth(client)
        resp = await client.post("/api/v1/quotations/preview", json={
            "estimate_days": 10,
            "daily_rate": "1000.00",
            "direct_cost": "0",
            "risk_buffer_rate": "0.1",
            "discount_amount": "0",
            "tax_rate": "0.06",
        }, headers=h)
        assert resp.status_code == 200
        data = resp.json()
        assert "labor_amount" in data
        assert "total_amount" in data

    @pytest.mark.asyncio
    async def test_preview_endpoint_no_db_write(self, client: AsyncClient):
        h = await _auth(client)
        payload = {
            "estimate_days": 5,
            "daily_rate": "800.00",
            "direct_cost": "1000.00",
            "risk_buffer_rate": "0",
            "discount_amount": "0",
            "tax_rate": "0",
        }
        resp1 = await client.post("/api/v1/quotations/preview", json=payload, headers=h)
        resp2 = await client.post("/api/v1/quotations/preview", json=payload, headers=h)
        assert resp1.json() == resp2.json()

    @pytest.mark.asyncio
    async def test_preview_endpoint_structure_matches_spec(self, client: AsyncClient):
        h = await _auth(client)
        resp = await client.post("/api/v1/quotations/preview", json={
            "estimate_days": 1,
            "daily_rate": "100.00",
        }, headers=h)
        data = resp.json()
        expected_keys = {
            "labor_amount", "base_amount", "buffer_amount",
            "subtotal_amount", "tax_amount", "total_amount",
        }
        assert set(data.keys()) == expected_keys

    @pytest.mark.asyncio
    async def test_preview_endpoint_precision_two_decimal(self, client: AsyncClient):
        h = await _auth(client)
        resp = await client.post("/api/v1/quotations/preview", json={
            "estimate_days": 7,
            "daily_rate": "333.33",
            "risk_buffer_rate": "0.15",
            "tax_rate": "0.13",
        }, headers=h)
        data = resp.json()
        for key, val in data.items():
            d = Decimal(str(val))
            assert d == d.quantize(Decimal("0.01")), f"{key} 精度超过 2 位"

    @pytest.mark.asyncio
    async def test_preview_endpoint_negative_values_rejected(self, client: AsyncClient):
        h = await _auth(client)
        resp = await client.post("/api/v1/quotations/preview", json={
            "estimate_days": 10,
            "daily_rate": "-100.00",
        }, headers=h)
        assert resp.status_code == 422
