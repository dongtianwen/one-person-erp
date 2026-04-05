"""项目管理模块测试 - FR-PROJECT"""
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


# --- FR-PROJ-01: 开始日期不能晚于结束日期 ---
async def test_project_start_after_end_rejected(client):
    """开始日期晚于结束日期应被拒绝"""
    h = await _auth(client)
    cid = await _create_customer(client, h)
    r = await client.post("/api/v1/projects", json={
        "name": "项目A", "customer_id": cid,
        "start_date": "2026-06-01", "end_date": "2026-05-01",
    }, headers=h)
    assert r.status_code == 400


async def test_project_start_before_end_accepted(client):
    """开始日期早于结束日期应成功"""
    h = await _auth(client)
    cid = await _create_customer(client, h)
    r = await client.post("/api/v1/projects", json={
        "name": "项目B", "customer_id": cid,
        "start_date": "2026-05-01", "end_date": "2026-06-01",
    }, headers=h)
    assert r.status_code == 201


# --- FR-PROJ-02: 所有里程碑完成后进度自动100% ---
async def test_progress_auto_100_when_all_milestones_completed(client):
    """所有里程碑完成时项目进度自动变为100%"""
    h = await _auth(client)
    cid = await _create_customer(client, h)
    r = await client.post("/api/v1/projects", json={"name": "P1", "customer_id": cid}, headers=h)
    pid = r.json()["id"]
    # 创建2个里程碑
    m1 = await client.post(f"/api/v1/projects/{pid}/milestones", json={"title": "M1", "due_date": "2026-05-01"}, headers=h)
    m2 = await client.post(f"/api/v1/projects/{pid}/milestones", json={"title": "M2", "due_date": "2026-06-01"}, headers=h)
    m1_id = m1.json()["id"]
    m2_id = m2.json()["id"]
    # 完成第一个
    await client.put(f"/api/v1/projects/milestones/{m1_id}", json={"is_completed": True}, headers=h)
    # 进度应为50%
    r = await client.get(f"/api/v1/projects/{pid}", headers=h)
    assert r.json()["project"]["progress"] == 50
    # 完成第二个
    await client.put(f"/api/v1/projects/milestones/{m2_id}", json={"is_completed": True}, headers=h)
    # 进度应为100%
    r = await client.get(f"/api/v1/projects/{pid}", headers=h)
    assert r.json()["project"]["progress"] == 100


# --- FR-PROJ-03: 预算变更必须记录原因 ---
async def test_budget_change_without_reason_rejected(client):
    """预算变更未填写原因应被拒绝"""
    h = await _auth(client)
    cid = await _create_customer(client, h)
    r = await client.post("/api/v1/projects", json={
        "name": "P2", "customer_id": cid, "budget": 10000,
    }, headers=h)
    pid = r.json()["id"]
    r2 = await client.put(f"/api/v1/projects/{pid}", json={"budget": 20000}, headers=h)
    assert r2.status_code == 400


async def test_budget_change_with_reason_accepted(client):
    """预算变更填写原因应成功"""
    h = await _auth(client)
    cid = await _create_customer(client, h)
    r = await client.post("/api/v1/projects", json={
        "name": "P3", "customer_id": cid, "budget": 10000,
    }, headers=h)
    pid = r.json()["id"]
    r2 = await client.put(f"/api/v1/projects/{pid}", json={"budget": 20000, "budget_change_reason": "客户追加需求"}, headers=h)
    assert r2.status_code == 200
    assert r2.json()["budget"] == 20000


# --- FR-PROJ-04: 项目详情包含任务和里程碑 ---
async def test_project_detail_includes_tasks_and_milestones(client):
    """项目详情返回任务和里程碑"""
    h = await _auth(client)
    cid = await _create_customer(client, h)
    r = await client.post("/api/v1/projects", json={"name": "P4", "customer_id": cid}, headers=h)
    pid = r.json()["id"]
    await client.post(f"/api/v1/projects/{pid}/tasks", json={"title": "任务1"}, headers=h)
    await client.post(f"/api/v1/projects/{pid}/milestones", json={"title": "里程碑1", "due_date": "2026-05-01"}, headers=h)
    r2 = await client.get(f"/api/v1/projects/{pid}", headers=h)
    assert r2.status_code == 200
    data = r2.json()
    assert len(data["tasks"]) == 1
    assert len(data["milestones"]) == 1


# --- 任务管理 ---
async def test_create_task(client):
    h = await _auth(client)
    cid = await _create_customer(client, h)
    r = await client.post("/api/v1/projects", json={"name": "P5", "customer_id": cid}, headers=h)
    pid = r.json()["id"]
    r2 = await client.post(f"/api/v1/projects/{pid}/tasks", json={
        "title": "任务1", "status": "todo", "priority": "high",
    }, headers=h)
    assert r2.status_code == 201
    assert r2.json()["title"] == "任务1"


async def test_update_task_status(client):
    h = await _auth(client)
    cid = await _create_customer(client, h)
    r = await client.post("/api/v1/projects", json={"name": "P6", "customer_id": cid}, headers=h)
    pid = r.json()["id"]
    r2 = await client.post(f"/api/v1/projects/{pid}/tasks", json={"title": "任务2"}, headers=h)
    tid = r2.json()["id"]
    r3 = await client.put(f"/api/v1/projects/tasks/{tid}", json={"status": "done"}, headers=h)
    assert r3.status_code == 200
    assert r3.json()["status"] == "done"


# --- 里程碑管理 ---
async def test_complete_milestone_sets_completed_date(client):
    """完成里程碑时自动设置完成日期"""
    h = await _auth(client)
    cid = await _create_customer(client, h)
    r = await client.post("/api/v1/projects", json={"name": "P7", "customer_id": cid}, headers=h)
    pid = r.json()["id"]
    r2 = await client.post(f"/api/v1/projects/{pid}/milestones", json={"title": "M1", "due_date": "2026-05-01"}, headers=h)
    mid = r2.json()["id"]
    r3 = await client.put(f"/api/v1/projects/milestones/{mid}", json={"is_completed": True}, headers=h)
    assert r3.status_code == 200
    assert r3.json()["is_completed"] is True
    assert r3.json()["completed_date"] is not None
