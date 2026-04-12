"""FR-1102 标注任务测试——覆盖状态转换、返工原因、规范写入 requirements 表。"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import get_db
from app.models.base import Base
from app.models.user import User
from app.models.customer import Customer
from app.models.project import Project
from app.models.dataset import Dataset, DatasetVersion
from app.core.security import get_password_hash

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


async def _login(client: AsyncClient) -> dict:
    r = await client.post("/api/v1/auth/login", data={"username": "admin", "password": "admin123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest_asyncio.fixture(scope="function")
async def db():
    engine = create_async_engine(TEST_DB_URL, echo=False, poolclass=StaticPool)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        admin = User(
            username="admin", hashed_password=get_password_hash("admin123"),
            full_name="管理员", email="admin@test.local", is_active=True, is_superuser=True,
        )
        session.add(admin)
        cust = Customer(name="测试客户", contact_person="张三", phone="13800000000")
        session.add(cust)
        await session.commit()
        proj = Project(name="测试项目", customer_id=cust.id)
        session.add(proj)
        await session.commit()
        ds = Dataset(project_id=proj.id, name="DS1")
        session.add(ds)
        await session.commit()
        dv = DatasetVersion(dataset_id=ds.id, version_no="v1.0", status="ready")
        session.add(dv)
        await session.commit()
        yield session, proj.id, dv.id
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def client(db):
    session, _, _ = db
    async def override_get_db():
        yield session
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


async def _create_task(client: AsyncClient, headers: dict, project_id: int, dv_id: int) -> int:
    r = await client.post(
        "/api/v1/annotation-tasks",
        json={"project_id": project_id, "dataset_version_id": dv_id, "name": "标注任务1"},
        headers=headers,
    )
    return r.json()["id"]


# ── FR-1102 测试用例 ──────────────────────────────────────────────


async def test_create_task_requires_dataset_version(client, db):
    """FR-1102 创建任务需要 dataset_version_id。"""
    _, project_id, _ = db
    headers = await _login(client)
    r = await client.post(
        "/api/v1/annotation-tasks",
        json={"project_id": project_id, "name": "任务1"},
        headers=headers,
    )
    assert r.status_code == 422


async def test_status_transitions_correct(client, db):
    """FR-1102 状态流转正确：pending→in_progress→quality_check→completed。"""
    _, project_id, dv_id = db
    headers = await _login(client)
    task_id = await _create_task(client, headers, project_id, dv_id)

    for target in ["in_progress", "quality_check", "completed"]:
        r = await client.patch(
            f"/api/v1/annotation-tasks/{task_id}/status",
            json={"status": target},
            headers=headers,
        )
        assert r.status_code == 200, f"转到 {target} 失败: {r.text}"


async def test_rework_reason_required(client, db):
    """FR-1102 rework 时 rework_reason 必填。"""
    _, project_id, dv_id = db
    headers = await _login(client)
    task_id = await _create_task(client, headers, project_id, dv_id)

    # 推进到 quality_check
    await client.patch(f"/api/v1/annotation-tasks/{task_id}/status", json={"status": "in_progress"}, headers=headers)
    await client.patch(f"/api/v1/annotation-tasks/{task_id}/status", json={"status": "quality_check"}, headers=headers)

    # rework 不带 rework_reason
    r = await client.patch(
        f"/api/v1/annotation-tasks/{task_id}/status",
        json={"status": "rework"},
        headers=headers,
    )
    assert r.status_code == 422


async def test_completed_is_terminal(client, db):
    """FR-1102 completed 为终态，不可再流转。"""
    _, project_id, dv_id = db
    headers = await _login(client)
    task_id = await _create_task(client, headers, project_id, dv_id)

    await client.patch(f"/api/v1/annotation-tasks/{task_id}/status", json={"status": "in_progress"}, headers=headers)
    await client.patch(f"/api/v1/annotation-tasks/{task_id}/status", json={"status": "quality_check"}, headers=headers)
    await client.patch(f"/api/v1/annotation-tasks/{task_id}/status", json={"status": "completed"}, headers=headers)

    r = await client.patch(
        f"/api/v1/annotation-tasks/{task_id}/status",
        json={"status": "in_progress"},
        headers=headers,
    )
    assert r.status_code == 409


async def test_create_spec_writes_to_requirements_table(client, db):
    """FR-1102 标注规范写入 requirements 表。"""
    _, project_id, dv_id = db
    headers = await _login(client)
    task_id = await _create_task(client, headers, project_id, dv_id)

    r = await client.post(
        f"/api/v1/annotation-tasks/{task_id}/specs",
        json={"title": "标注规范v1", "content": "按要求标注所有图片"},
        headers=headers,
    )
    assert r.status_code == 200
    assert "id" in r.json()


async def test_spec_has_correct_type_and_task_id(client, db):
    """FR-1102 规范的 requirement_type 和 annotation_task_id 正确。"""
    session, project_id, dv_id = db
    headers = await _login(client)
    task_id = await _create_task(client, headers, project_id, dv_id)

    await client.post(
        f"/api/v1/annotation-tasks/{task_id}/specs",
        json={"title": "标注规范v1", "content": "按要求标注所有图片"},
        headers=headers,
    )

    from sqlalchemy import select
    from app.models.requirement import Requirement
    stmt = select(Requirement).where(Requirement.annotation_task_id == task_id)
    result = await session.execute(stmt)
    req = result.scalar_one()
    assert req.requirement_type == "annotation_spec"
    assert req.annotation_task_id == task_id


async def test_annotation_content_not_in_task_table(client, db):
    """FR-1102 annotation_tasks 表不存储规范内容。"""
    _, project_id, dv_id = db
    headers = await _login(client)
    task_id = await _create_task(client, headers, project_id, dv_id)

    await client.post(
        f"/api/v1/annotation-tasks/{task_id}/specs",
        json={"title": "标注规范v1", "content": "按要求标注所有图片"},
        headers=headers,
    )

    # 任务详情不应包含规范内容字段
    r = await client.get(f"/api/v1/annotation-tasks/{task_id}", headers=headers)
    data = r.json()
    assert "quality_check_result" not in data or data["quality_check_result"] is None
    assert "content" not in data


async def test_invalid_transition_returns_409(client, db):
    """FR-1102 非法状态转换返回 409。"""
    _, project_id, dv_id = db
    headers = await _login(client)
    task_id = await _create_task(client, headers, project_id, dv_id)

    # pending 不能直接转到 completed
    r = await client.patch(
        f"/api/v1/annotation-tasks/{task_id}/status",
        json={"status": "completed"},
        headers=headers,
    )
    assert r.status_code == 409
