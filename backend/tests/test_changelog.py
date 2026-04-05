"""变更日志模块测试 - FR-CHANGELOG

业务规则：
- 财务记录修改时，自动记录变更前后值到变更日志
- 项目预算变更时，自动记录变更前后值
- 合同金额变更时，自动记录变更前后值
- 变更日志不可修改、不可删除
"""
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


# --- FR-CL-01: 财务记录修改记录变更日志 ---
async def test_finance_update_creates_changelog(client):
    """修改财务记录金额时自动创建变更日志"""
    h = await _auth(client)
    r = await client.post("/api/v1/finances", json={
        "type": "income", "amount": 1000, "date": "2026-04-01", "status": "confirmed",
    }, headers=h)
    rid = r.json()["id"]
    r2 = await client.put(f"/api/v1/finances/{rid}", json={"amount": 2000}, headers=h)
    assert r2.status_code == 200

    # 查询变更日志
    r3 = await client.get(f"/api/v1/changelogs?entity_type=finance_record&entity_id={rid}", headers=h)
    assert r3.status_code == 200
    logs = r3.json()
    assert len(logs) >= 1
    log = logs[0]
    assert log["field"] == "amount"
    assert log["old_value"] == "1000.0"
    assert log["new_value"] == "2000.0"


async def test_finance_update_multiple_fields_creates_multiple_logs(client):
    """修改多个字段时每字段各生成一条变更日志"""
    h = await _auth(client)
    r = await client.post("/api/v1/finances", json={
        "type": "income", "amount": 1000, "date": "2026-04-01",
        "description": "旧描述",
    }, headers=h)
    rid = r.json()["id"]
    await client.put(f"/api/v1/finances/{rid}", json={
        "amount": 3000, "description": "新描述",
    }, headers=h)
    r3 = await client.get(f"/api/v1/changelogs?entity_type=finance_record&entity_id={rid}", headers=h)
    logs = r3.json()
    fields = {log["field"] for log in logs}
    assert "amount" in fields
    assert "description" in fields


# --- FR-CL-02: 项目预算变更记录变更日志 ---
async def test_project_budget_change_creates_changelog(client):
    """项目预算变更时自动创建变更日志"""
    h = await _auth(client)
    r = await client.post("/api/v1/customers", json={
        "name": "C", "contact_person": "张三", "company": "公司X", "source": "other", "status": "deal",
    }, headers=h)
    cid = r.json()["id"]
    r = await client.post("/api/v1/projects", json={
        "name": "P1", "customer_id": cid, "budget": 10000,
    }, headers=h)
    pid = r.json()["id"]
    await client.put(f"/api/v1/projects/{pid}", json={
        "budget": 20000, "budget_change_reason": "追加需求",
    }, headers=h)

    r3 = await client.get(f"/api/v1/changelogs?entity_type=project&entity_id={pid}", headers=h)
    assert r3.status_code == 200
    logs = r3.json()
    assert len(logs) >= 1
    budget_log = [l for l in logs if l["field"] == "budget"][0]
    assert budget_log["old_value"] == "10000.0"
    assert budget_log["new_value"] == "20000.0"


# --- FR-CL-03: 合同金额变更记录变更日志 ---
async def test_contract_amount_change_creates_changelog(client):
    """合同金额变更时自动创建变更日志"""
    h = await _auth(client)
    r = await client.post("/api/v1/customers", json={
        "name": "C2", "contact_person": "李四", "company": "公司Y", "source": "other", "status": "deal",
    }, headers=h)
    cid = r.json()["id"]
    r = await client.post("/api/v1/contracts", json={
        "title": "合同1", "customer_id": cid, "amount": 5000,
    }, headers=h)
    contract_id = r.json()["id"]
    await client.put(f"/api/v1/contracts/{contract_id}", json={"amount": 8000}, headers=h)

    r3 = await client.get(f"/api/v1/changelogs?entity_type=contract&entity_id={contract_id}", headers=h)
    assert r3.status_code == 200
    logs = r3.json()
    assert len(logs) >= 1
    amount_log = [l for l in logs if l["field"] == "amount"][0]
    assert amount_log["old_value"] == "5000.0"
    assert amount_log["new_value"] == "8000.0"


# --- FR-CL-04: 变更日志只读 ---
async def test_changelog_contains_metadata(client):
    """变更日志包含操作人、时间等元数据"""
    h = await _auth(client)
    r = await client.post("/api/v1/finances", json={
        "type": "income", "amount": 1000, "date": "2026-04-01",
    }, headers=h)
    rid = r.json()["id"]
    await client.put(f"/api/v1/finances/{rid}", json={"amount": 2000}, headers=h)
    r3 = await client.get(f"/api/v1/changelogs?entity_type=finance_record&entity_id={rid}", headers=h)
    log = r3.json()[0]
    assert "changed_by" in log
    assert "created_at" in log
    assert "entity_type" in log
    assert "entity_id" in log
