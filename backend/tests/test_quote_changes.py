"""v1.6 报价变更日志测试——FR-603"""
import pytest
import pytest_asyncio
from datetime import date, timedelta

from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
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
        "name": "变更日志客户",
        "contact_person": "张三",
        "phone": "13800138000",
    }, headers=h)
    return resp.json()["id"]


class TestQuoteChanges:
    """FR-603: 变更日志测试。"""

    @pytest.mark.asyncio
    async def test_quote_changes_table_exists(self, db_session):
        result = await db_session.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='quotation_changes'"
        ))
        assert result.scalar() == "quotation_changes"

    def test_quote_changes_change_type_enum_defined(self):
        from app.models.enums import QuoteChangeType
        assert QuoteChangeType.FIELD_UPDATE.value == "field_update"
        assert QuoteChangeType.STATUS_CHANGE.value == "status_change"
        assert QuoteChangeType.CONVERTED.value == "converted"

    @pytest.mark.asyncio
    async def test_quote_changes_record_field_update_log(self, client: AsyncClient, db_session):
        h = await _auth(client)
        cid = await _create_customer(client, h)
        resp = await client.post("/api/v1/quotations", json={
            "title": "变更测试", "customer_id": cid,
            "requirement_summary": "需求", "estimate_days": 10,
            "valid_until": str(date.today() + timedelta(days=30)),
        }, headers=h)
        qid = resp.json()["id"]
        await client.put(f"/api/v1/quotations/{qid}", json={"title": "新标题"}, headers=h)
        result = await db_session.execute(text(
            "SELECT change_type FROM quotation_changes WHERE quotation_id = :qid"
        ), {"qid": qid})
        changes = result.fetchall()
        assert len(changes) >= 1
        assert any(c[0] == "field_update" for c in changes)

    @pytest.mark.asyncio
    async def test_quote_changes_record_status_change_log(self, client: AsyncClient, db_session):
        h = await _auth(client)
        cid = await _create_customer(client, h)
        resp = await client.post("/api/v1/quotations", json={
            "title": "状态变更测试", "customer_id": cid,
            "requirement_summary": "需求", "estimate_days": 10,
            "valid_until": str(date.today() + timedelta(days=30)),
        }, headers=h)
        qid = resp.json()["id"]
        await client.post(f"/api/v1/quotations/{qid}/send", headers=h)
        result = await db_session.execute(text(
            "SELECT change_type FROM quotation_changes WHERE quotation_id = :qid"
        ), {"qid": qid})
        changes = result.fetchall()
        assert len(changes) >= 1

    @pytest.mark.asyncio
    async def test_quote_changes_record_converted_log(self, client: AsyncClient, db_session):
        h = await _auth(client)
        cid = await _create_customer(client, h)
        resp = await client.post("/api/v1/quotations", json={
            "title": "转合同日志测试", "customer_id": cid,
            "requirement_summary": "需求", "estimate_days": 10,
            "daily_rate": "1000.00",
            "valid_until": str(date.today() + timedelta(days=30)),
        }, headers=h)
        qid = resp.json()["id"]
        await client.post(f"/api/v1/quotations/{qid}/send", headers=h)
        await client.post(f"/api/v1/quotations/{qid}/accept", headers=h)
        await client.post(f"/api/v1/quotations/{qid}/convert-to-contract", headers=h)
        result = await db_session.execute(text(
            "SELECT change_type FROM quotation_changes WHERE quotation_id = :qid"
        ), {"qid": qid})
        changes = result.fetchall()
        assert any(c[0] == "converted" for c in changes)
