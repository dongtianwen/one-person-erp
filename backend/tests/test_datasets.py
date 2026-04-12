"""FR-1101 数据集台账测试——覆盖版本号校验、冻结规则、in_use 保护、状态转换、404。"""
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
        yield session, proj.id
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def client(db):
    session, _ = db
    async def override_get_db():
        yield session
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


async def _create_dataset(client: AsyncClient, headers: dict, project_id: int) -> int:
    r = await client.post(
        "/api/v1/datasets",
        json={"project_id": project_id, "name": "DS1", "dataset_type": "image"},
        headers=headers,
    )
    return r.json()["id"]


async def _create_version(
    client: AsyncClient, headers: dict, dataset_id: int,
    version_no: str = "v1.0", **kwargs,
) -> int:
    data = {"version_no": version_no, **kwargs}
    r = await client.post(
        f"/api/v1/datasets/{dataset_id}/versions",
        json=data,
        headers=headers,
    )
    return r.json()["id"]


# ── FR-1101 测试用例 ──────────────────────────────────────────────


async def test_create_dataset_version_with_metadata_fields(client, db):
    """FR-1101 创建版本时包含元数据字段。"""
    _, project_id = db
    headers = await _login(client)
    ds_id = await _create_dataset(client, headers, project_id)
    r = await client.post(
        f"/api/v1/datasets/{ds_id}/versions",
        json={
            "version_no": "v1.0",
            "data_source": "公开数据集",
            "label_schema_version": "v2",
            "change_summary": "初始版本",
            "sample_count": 1000,
        },
        headers=headers,
    )
    assert r.status_code == 200
    version_id = r.json()["id"]

    r = await client.get(f"/api/v1/datasets/versions/{version_id}", headers=headers)
    data = r.json()
    assert data["data_source"] == "公开数据集"
    assert data["label_schema_version"] == "v2"
    assert data["change_summary"] == "初始版本"
    assert data["sample_count"] == 1000


async def test_version_no_format_validated(client, db):
    """FR-1101 版本号格式校验。"""
    _, project_id = db
    headers = await _login(client)
    ds_id = await _create_dataset(client, headers, project_id)

    r = await client.post(
        f"/api/v1/datasets/{ds_id}/versions",
        json={"version_no": "1.0"},
        headers=headers,
    )
    assert r.status_code == 422


async def test_version_no_unique_per_dataset(client, db):
    """FR-1101 同数据集下版本号唯一。"""
    _, project_id = db
    headers = await _login(client)
    ds_id = await _create_dataset(client, headers, project_id)

    r1 = await client.post(
        f"/api/v1/datasets/{ds_id}/versions",
        json={"version_no": "v1.0"},
        headers=headers,
    )
    assert r1.status_code == 200

    r2 = await client.post(
        f"/api/v1/datasets/{ds_id}/versions",
        json={"version_no": "v1.0"},
        headers=headers,
    )
    assert r2.status_code in (409, 500)  # 唯一约束违反


async def test_frozen_fields_rejected_when_ready(client, db):
    """FR-1101 ready 状态下冻结字段不可修改。"""
    _, project_id = db
    headers = await _login(client)
    ds_id = await _create_dataset(client, headers, project_id)
    v_id = await _create_version(client, headers, ds_id, sample_count=100)

    # 转为 ready
    await client.patch(f"/api/v1/datasets/versions/{v_id}/ready", headers=headers)

    # 尝试修改冻结字段
    r = await client.put(
        f"/api/v1/datasets/versions/{v_id}",
        json={"sample_count": 200},
        headers=headers,
    )
    assert r.status_code == 409


async def test_frozen_fields_rejected_when_in_use(client, db):
    """FR-1101 in_use 状态下冻结字段不可修改。"""
    _, project_id = db
    headers = await _login(client)
    ds_id = await _create_dataset(client, headers, project_id)
    v_id = await _create_version(client, headers, ds_id)

    # 直接设置 in_use（模拟系统操作）
    session, _ = db
    from sqlalchemy import select
    stmt = select(DatasetVersion).where(DatasetVersion.id == v_id)
    result = await session.execute(stmt)
    ver = result.scalar_one()
    ver.status = "in_use"
    await session.commit()

    r = await client.put(
        f"/api/v1/datasets/versions/{v_id}",
        json={"sample_count": 200},
        headers=headers,
    )
    assert r.status_code == 409


async def test_notes_mutable_when_frozen(client, db):
    """FR-1101 notes 在冻结状态下仍可修改。"""
    _, project_id = db
    headers = await _login(client)
    ds_id = await _create_dataset(client, headers, project_id)
    v_id = await _create_version(client, headers, ds_id)

    await client.patch(f"/api/v1/datasets/versions/{v_id}/ready", headers=headers)

    r = await client.put(
        f"/api/v1/datasets/versions/{v_id}",
        json={"notes": "新备注"},
        headers=headers,
    )
    assert r.status_code == 200


async def test_change_summary_mutable_when_frozen(client, db):
    """FR-1101 change_summary 在冻结状态下仍可修改。"""
    _, project_id = db
    headers = await _login(client)
    ds_id = await _create_dataset(client, headers, project_id)
    v_id = await _create_version(client, headers, ds_id)

    await client.patch(f"/api/v1/datasets/versions/{v_id}/ready", headers=headers)

    r = await client.put(
        f"/api/v1/datasets/versions/{v_id}",
        json={"change_summary": "更新了标注"},
        headers=headers,
    )
    assert r.status_code == 200


async def test_in_use_not_accepted_via_api(client, db):
    """FR-1101 接口不可直接设置 in_use 状态。"""
    _, project_id = db
    headers = await _login(client)
    ds_id = await _create_dataset(client, headers, project_id)

    r = await client.post(
        f"/api/v1/datasets/{ds_id}/versions",
        json={"version_no": "v1.0", "status": "in_use"},
        headers=headers,
    )
    assert r.status_code == 422


async def test_in_use_version_cannot_delete(client, db):
    """FR-1101 in_use 版本不可删除。"""
    _, project_id = db
    headers = await _login(client)
    ds_id = await _create_dataset(client, headers, project_id)
    v_id = await _create_version(client, headers, ds_id)

    session, _ = db
    from sqlalchemy import select
    stmt = select(DatasetVersion).where(DatasetVersion.id == v_id)
    result = await session.execute(stmt)
    ver = result.scalar_one()
    ver.status = "in_use"
    await session.commit()

    r = await client.delete(f"/api/v1/datasets/versions/{v_id}", headers=headers)
    assert r.status_code == 409


async def test_ready_transition_success(client, db):
    """FR-1101 draft → ready 成功。"""
    _, project_id = db
    headers = await _login(client)
    ds_id = await _create_dataset(client, headers, project_id)
    v_id = await _create_version(client, headers, ds_id)

    r = await client.patch(f"/api/v1/datasets/versions/{v_id}/ready", headers=headers)
    assert r.status_code == 200

    r = await client.get(f"/api/v1/datasets/versions/{v_id}", headers=headers)
    assert r.json()["status"] == "ready"


async def test_archive_transition_success(client, db):
    """FR-1101 ready → archived 成功。"""
    _, project_id = db
    headers = await _login(client)
    ds_id = await _create_dataset(client, headers, project_id)
    v_id = await _create_version(client, headers, ds_id)

    await client.patch(f"/api/v1/datasets/versions/{v_id}/ready", headers=headers)
    r = await client.patch(f"/api/v1/datasets/versions/{v_id}/archive", headers=headers)
    assert r.status_code == 200

    r = await client.get(f"/api/v1/datasets/versions/{v_id}", headers=headers)
    assert r.json()["status"] == "archived"


async def test_dataset_not_found_returns_404(client, db):
    """FR-1101 数据集不存在返回 404。"""
    headers = await _login(client)
    r = await client.get("/api/v1/datasets/99999", headers=headers)
    assert r.status_code == 404


async def test_version_not_found_returns_404(client, db):
    """FR-1101 版本不存在返回 404。"""
    headers = await _login(client)
    r = await client.get("/api/v1/datasets/versions/99999", headers=headers)
    assert r.status_code == 404
