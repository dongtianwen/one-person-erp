"""财务管理模块测试 - FR-FINANCE"""
import pytest
import pytest_asyncio
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


async def _auth(client):
    r = await client.post("/api/v1/auth/login", data={"username": "admin", "password": "admin123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# --- FR-FIN-01: 收入记录可选关联合同 ---
async def test_income_without_contract(client):
    """收入记录不关联合同也可以创建"""
    h = await _auth(client)
    r = await client.post("/api/v1/finances", json={
        "type": "income", "amount": 5000, "date": "2026-04-01", "description": "服务费",
    }, headers=h)
    assert r.status_code == 201
    assert r.json()["contract_id"] is None


async def test_income_with_contract(client):
    """收入记录关联合同也可以创建"""
    h = await _auth(client)
    r = await client.post("/api/v1/customers", json={
        "name": "客户", "contact_person": "张三", "company": "公司",
        "source": "other", "status": "deal",
    }, headers=h)
    cid = r.json()["id"]
    r = await client.post("/api/v1/contracts", json={"title": "合同", "customer_id": cid, "amount": 10000}, headers=h)
    contract_id = r.json()["id"]
    r = await client.post("/api/v1/finances", json={
        "type": "income", "amount": 5000, "date": "2026-04-01", "contract_id": contract_id,
    }, headers=h)
    assert r.status_code == 201
    assert r.json()["contract_id"] == contract_id


# --- FR-FIN-02: 发票号码全局唯一 ---
async def test_invoice_no_unique(client):
    """发票号码全局唯一"""
    h = await _auth(client)
    await client.post("/api/v1/finances", json={
        "type": "income", "amount": 1000, "date": "2026-04-01", "invoice_no": "INV-001",
        "invoice_direction": "output", "invoice_type": "general", "tax_rate": 0.06,
    }, headers=h)
    r = await client.post("/api/v1/finances", json={
        "type": "income", "amount": 2000, "date": "2026-04-02", "invoice_no": "INV-001",
        "invoice_direction": "output", "invoice_type": "general", "tax_rate": 0.06,
    }, headers=h)
    assert r.status_code == 400


async def test_invoice_no_update_conflict(client):
    """更新时发票号码不能与其他记录冲突"""
    h = await _auth(client)
    r1 = await client.post("/api/v1/finances", json={
        "type": "income", "amount": 1000, "date": "2026-04-01", "invoice_no": "INV-002",
        "invoice_direction": "output", "invoice_type": "general", "tax_rate": 0.06,
    }, headers=h)
    r2 = await client.post("/api/v1/finances", json={
        "type": "income", "amount": 2000, "date": "2026-04-02", "invoice_no": "INV-003",
        "invoice_direction": "output", "invoice_type": "general", "tax_rate": 0.06,
    }, headers=h)
    id2 = r2.json()["id"]
    r3 = await client.put(f"/api/v1/finances/{id2}", json={"invoice_no": "INV-002"}, headers=h)
    assert r3.status_code == 400


async def test_invoice_no_same_record_update_ok(client):
    """更新为自身相同的发票号应允许"""
    h = await _auth(client)
    r = await client.post("/api/v1/finances", json={
        "type": "income", "amount": 1000, "date": "2026-04-01", "invoice_no": "INV-010",
        "invoice_direction": "output", "invoice_type": "general", "tax_rate": 0.06,
    }, headers=h)
    rid = r.json()["id"]
    r2 = await client.put(f"/api/v1/finances/{rid}", json={"invoice_no": "INV-010"}, headers=h)
    assert r2.status_code == 200


# --- FR-FIN-03: 月度报表 - 净利润 = 收入 - 支出 ---
async def test_monthly_summary_calculation(client):
    """月度净利润 = 总收入 - 总支出"""
    h = await _auth(client)
    # 创建已确认的收入和支出
    await client.post("/api/v1/finances", json={
        "type": "income", "amount": 10000, "date": "2026-04-10", "status": "confirmed",
    }, headers=h)
    await client.post("/api/v1/finances", json={
        "type": "expense", "amount": 3000, "date": "2026-04-15", "status": "confirmed",
        "funding_source": "company_account",
    }, headers=h)
    r = await client.get("/api/v1/finances/stats/monthly?year=2026&month=4", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert data["income"] == 10000
    assert data["expense"] == 3000
    assert data["profit"] == 7000


async def test_monthly_summary_excludes_unconfirmed(client):
    """月度报表不包含未确认的记录"""
    h = await _auth(client)
    await client.post("/api/v1/finances", json={
        "type": "income", "amount": 5000, "date": "2026-05-01", "status": "pending",
    }, headers=h)
    r = await client.get("/api/v1/finances/stats/monthly?year=2026&month=5", headers=h)
    assert r.status_code == 200
    assert r.json()["income"] == 0


# --- FR-FIN-04: 已确认财务记录可修改 ---
async def test_update_finance_record(client):
    """已确认的财务记录可以修改"""
    h = await _auth(client)
    r = await client.post("/api/v1/finances", json={
        "type": "income", "amount": 1000, "date": "2026-04-01", "status": "confirmed",
    }, headers=h)
    rid = r.json()["id"]
    r2 = await client.put(f"/api/v1/finances/{rid}", json={"amount": 2000, "description": "修改金额"}, headers=h)
    assert r2.status_code == 200
    assert r2.json()["amount"] == 2000


# --- FR-FIN-05: 财务记录列表筛选 ---
async def test_finance_list_filter_by_type(client):
    """按类型筛选财务记录"""
    h = await _auth(client)
    await client.post("/api/v1/finances", json={"type": "income", "amount": 1000, "date": "2026-04-01"}, headers=h)
    await client.post("/api/v1/finances", json={"type": "expense", "amount": 500, "date": "2026-04-02"}, headers=h)
    r = await client.get("/api/v1/finances?type=income", headers=h)
    assert r.status_code == 200
    assert all(item["type"] == "income" for item in r.json()["items"])
