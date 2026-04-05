"""客户管理模块测试 - FR-CUSTOMER"""
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
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# --- FR-CUST-01: 同一公司+联系人组合视为重复客户 ---
async def test_create_customer_success(client):
    h = await _auth(client)
    r = await client.post("/api/v1/customers", json={
        "name": "客户A", "contact_person": "张三", "company": "测试公司",
        "source": "referral", "status": "potential",
    }, headers=h)
    assert r.status_code == 201
    assert r.json()["name"] == "客户A"


async def test_duplicate_customer_rejected(client):
    """同一公司+联系人不能重复创建"""
    h = await _auth(client)
    payload = {"name": "客户A", "contact_person": "张三", "company": "测试公司", "source": "other", "status": "potential"}
    r1 = await client.post("/api/v1/customers", json=payload, headers=h)
    assert r1.status_code == 201
    r2 = await client.post("/api/v1/customers", json=payload, headers=h)
    assert r2.status_code == 400


async def test_same_company_different_contact_allowed(client):
    """同公司不同联系人可以创建"""
    h = await _auth(client)
    r1 = await client.post("/api/v1/customers", json={
        "name": "A", "contact_person": "张三", "company": "公司X", "source": "other", "status": "potential",
    }, headers=h)
    assert r1.status_code == 201
    r2 = await client.post("/api/v1/customers", json={
        "name": "B", "contact_person": "李四", "company": "公司X", "source": "other", "status": "potential",
    }, headers=h)
    assert r2.status_code == 201


# --- FR-CUST-02: 流失必须填原因 ---
async def test_lost_without_reason_rejected(client):
    """状态变更为流失时未填原因应被拒绝"""
    h = await _auth(client)
    r = await client.post("/api/v1/customers", json={
        "name": "C", "contact_person": "王五", "company": "公司Y", "source": "other", "status": "potential",
    }, headers=h)
    cid = r.json()["id"]
    r2 = await client.put(f"/api/v1/customers/{cid}", json={"status": "lost"}, headers=h)
    assert r2.status_code == 400


async def test_lost_with_reason_accepted(client):
    """状态变更为流失且填了原因应成功"""
    h = await _auth(client)
    r = await client.post("/api/v1/customers", json={
        "name": "C", "contact_person": "王五", "company": "公司Y", "source": "other", "status": "potential",
    }, headers=h)
    cid = r.json()["id"]
    r2 = await client.put(f"/api/v1/customers/{cid}", json={"status": "lost", "lost_reason": "价格太高"}, headers=h)
    assert r2.status_code == 200
    assert r2.json()["status"] == "lost"


# --- FR-CUST-03: 有关联项目或合同的客户禁止删除 ---
async def test_delete_customer_with_project_rejected(client):
    """有关联项目的客户不能删除"""
    h = await _auth(client)
    r = await client.post("/api/v1/customers", json={
        "name": "D", "contact_person": "赵六", "company": "公司Z", "source": "other", "status": "deal",
    }, headers=h)
    cid = r.json()["id"]
    await client.post("/api/v1/projects", json={"name": "P1", "customer_id": cid}, headers=h)
    r2 = await client.delete(f"/api/v1/customers/{cid}", headers=h)
    assert r2.status_code == 400


async def test_delete_customer_with_contract_rejected(client):
    """有关联合同的客户不能删除"""
    h = await _auth(client)
    r = await client.post("/api/v1/customers", json={
        "name": "E", "contact_person": "孙七", "company": "公司W", "source": "other", "status": "deal",
    }, headers=h)
    cid = r.json()["id"]
    await client.post("/api/v1/contracts", json={"title": "合同1", "customer_id": cid, "amount": 5000}, headers=h)
    r2 = await client.delete(f"/api/v1/customers/{cid}", headers=h)
    assert r2.status_code == 400


async def test_delete_customer_without_associations(client):
    """无关联的客户可以删除"""
    h = await _auth(client)
    r = await client.post("/api/v1/customers", json={
        "name": "F", "contact_person": "周八", "company": "公司V", "source": "other", "status": "potential",
    }, headers=h)
    cid = r.json()["id"]
    r2 = await client.delete(f"/api/v1/customers/{cid}", headers=h)
    assert r2.status_code == 200


# --- FR-CUST-04: 成交不触发自动操作 ---
async def test_deal_status_no_side_effects(client):
    """状态变为成交不触发额外操作"""
    h = await _auth(client)
    r = await client.post("/api/v1/customers", json={
        "name": "G", "contact_person": "吴九", "company": "公司U", "source": "other", "status": "follow_up",
    }, headers=h)
    cid = r.json()["id"]
    r2 = await client.put(f"/api/v1/customers/{cid}", json={"status": "deal"}, headers=h)
    assert r2.status_code == 200
    assert r2.json()["status"] == "deal"


# --- FR-CUST-05: 客户详情包含关联数据 ---
async def test_customer_detail_includes_projects_and_contracts(client):
    """客户详情返回关联项目和合同"""
    h = await _auth(client)
    r = await client.post("/api/v1/customers", json={
        "name": "H", "contact_person": "郑十", "company": "公司T", "source": "other", "status": "deal",
    }, headers=h)
    cid = r.json()["id"]
    await client.post("/api/v1/projects", json={"name": "P2", "customer_id": cid}, headers=h)
    await client.post("/api/v1/contracts", json={"title": "合同2", "customer_id": cid, "amount": 10000}, headers=h)
    r2 = await client.get(f"/api/v1/customers/{cid}", headers=h)
    assert r2.status_code == 200
    data = r2.json()
    assert "customer" in data
    assert len(data["projects"]) == 1
    assert len(data["contracts"]) == 1
