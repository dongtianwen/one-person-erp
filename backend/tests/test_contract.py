"""合同管理模块测试 - FR-CONTRACT"""
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


async def _create_customer(client, h):
    r = await client.post("/api/v1/customers", json={
        "name": "测试客户", "contact_person": "张三", "company": "测试公司",
        "source": "other", "status": "deal",
    }, headers=h)
    return r.json()["id"]


# --- FR-CONT-01: 合同编号自动生成 HT-YYYYMMDD-序号 ---
async def test_contract_no_auto_generated(client):
    """合同编号自动生成，格式 HT-YYYYMMDD-001"""
    h = await _auth(client)
    cid = await _create_customer(client, h)
    r = await client.post("/api/v1/contracts", json={
        "title": "测试合同", "customer_id": cid, "amount": 10000,
    }, headers=h)
    assert r.status_code == 201
    contract_no = r.json()["contract_no"]
    assert contract_no.startswith("HT-")
    # 格式为 HT-YYYYMMDD-NNN
    parts = contract_no.split("-")
    assert len(parts) == 3
    assert len(parts[2]) == 3


async def test_contract_no_sequential(client):
    """同日合同编号递增"""
    h = await _auth(client)
    cid = await _create_customer(client, h)
    r1 = await client.post("/api/v1/contracts", json={"title": "合同1", "customer_id": cid, "amount": 10000}, headers=h)
    r2 = await client.post("/api/v1/contracts", json={"title": "合同2", "customer_id": cid, "amount": 20000}, headers=h)
    no1 = r1.json()["contract_no"]
    no2 = r2.json()["contract_no"]
    seq1 = int(no1.split("-")[-1])
    seq2 = int(no2.split("-")[-1])
    assert seq2 == seq1 + 1


# --- FR-CONT-02: 状态只能按顺序流转 ---
async def test_contract_status_sequential_flow(client):
    """合同状态顺序流转：draft → active → executing → completed"""
    h = await _auth(client)
    cid = await _create_customer(client, h)
    r = await client.post("/api/v1/contracts", json={"title": "C1", "customer_id": cid, "amount": 10000}, headers=h)
    assert r.json()["status"] == "draft"
    contract_id = r.json()["id"]

    # draft → active
    r = await client.put(f"/api/v1/contracts/{contract_id}", json={"status": "active"}, headers=h)
    assert r.status_code == 200
    assert r.json()["status"] == "active"

    # active → executing
    r = await client.put(f"/api/v1/contracts/{contract_id}", json={"status": "executing"}, headers=h)
    assert r.status_code == 200
    assert r.json()["status"] == "executing"

    # executing → completed
    r = await client.put(f"/api/v1/contracts/{contract_id}", json={"status": "completed"}, headers=h)
    assert r.status_code == 200
    assert r.json()["status"] == "completed"


async def test_contract_status_skip_rejected(client):
    """合同状态不可跳跃"""
    h = await _auth(client)
    cid = await _create_customer(client, h)
    r = await client.post("/api/v1/contracts", json={"title": "C2", "customer_id": cid, "amount": 10000}, headers=h)
    contract_id = r.json()["id"]
    # draft → executing (跳跃)
    r = await client.put(f"/api/v1/contracts/{contract_id}", json={"status": "executing"}, headers=h)
    assert r.status_code == 400


# --- FR-CONT-03: 合同终止必须填写原因 ---
async def test_terminate_without_reason_rejected(client):
    """合同终止未填原因应被拒绝"""
    h = await _auth(client)
    cid = await _create_customer(client, h)
    r = await client.post("/api/v1/contracts", json={"title": "C3", "customer_id": cid, "amount": 10000}, headers=h)
    contract_id = r.json()["id"]
    # 先激活
    await client.put(f"/api/v1/contracts/{contract_id}", json={"status": "active"}, headers=h)
    # 尝试终止不填原因
    r = await client.put(f"/api/v1/contracts/{contract_id}", json={"status": "terminated"}, headers=h)
    assert r.status_code == 400


async def test_terminate_with_reason_accepted(client):
    """合同终止填写原因应成功"""
    h = await _auth(client)
    cid = await _create_customer(client, h)
    r = await client.post("/api/v1/contracts", json={"title": "C4", "customer_id": cid, "amount": 10000}, headers=h)
    contract_id = r.json()["id"]
    await client.put(f"/api/v1/contracts/{contract_id}", json={"status": "active"}, headers=h)
    r = await client.put(f"/api/v1/contracts/{contract_id}", json={"status": "terminated", "termination_reason": "客户违约"}, headers=h)
    assert r.status_code == 200
    assert r.json()["status"] == "terminated"


# --- FR-CONT-04: 合同金额变更同步项目预算 ---
async def test_contract_amount_syncs_to_project(client):
    """合同金额变更后关联项目预算同步更新"""
    h = await _auth(client)
    cid = await _create_customer(client, h)
    # 创建项目
    r = await client.post("/api/v1/projects", json={"name": "P1", "customer_id": cid, "budget": 10000}, headers=h)
    pid = r.json()["id"]
    # 创建合同并关联项目
    r = await client.post("/api/v1/contracts", json={
        "title": "C5", "customer_id": cid, "project_id": pid, "amount": 10000,
    }, headers=h)
    contract_id = r.json()["id"]
    # 更新合同金额
    r = await client.put(f"/api/v1/contracts/{contract_id}", json={"amount": 20000}, headers=h)
    assert r.status_code == 200
    # 检查项目预算是否同步
    r2 = await client.get(f"/api/v1/projects/{pid}", headers=h)
    assert r2.json()["project"]["budget"] == 20000


# --- FR-CONT-05: 生效中的合同不可删除 ---
async def test_delete_active_contract_rejected(client):
    """生效中的合同不可删除"""
    h = await _auth(client)
    cid = await _create_customer(client, h)
    r = await client.post("/api/v1/contracts", json={"title": "C6", "customer_id": cid, "amount": 5000}, headers=h)
    contract_id = r.json()["id"]
    await client.put(f"/api/v1/contracts/{contract_id}", json={"status": "active"}, headers=h)
    r = await client.delete(f"/api/v1/contracts/{contract_id}", headers=h)
    assert r.status_code == 400


async def test_delete_draft_contract_accepted(client):
    """草稿状态的合同可以删除"""
    h = await _auth(client)
    cid = await _create_customer(client, h)
    r = await client.post("/api/v1/contracts", json={"title": "C7", "customer_id": cid, "amount": 5000}, headers=h)
    contract_id = r.json()["id"]
    r = await client.delete(f"/api/v1/contracts/{contract_id}", headers=h)
    assert r.status_code == 200
