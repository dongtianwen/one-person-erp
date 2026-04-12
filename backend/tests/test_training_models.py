"""FR-1103 训练实验与模型版本测试——覆盖 in_use、冻结规则、可追溯性、删除保护。"""
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
from app.models.customer import Customer
from app.models.project import Project
from app.models.dataset import Dataset, DatasetVersion
from app.models.training_experiment import TrainingExperiment
from app.models.model_version import ModelVersion
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


async def _create_experiment(client: AsyncClient, headers: dict, project_id: int) -> int:
    r = await client.post(
        "/api/v1/training-experiments",
        json={"project_id": project_id, "name": "EXP1", "framework": "pytorch"},
        headers=headers,
    )
    return r.json()["id"]


async def _create_model_version(
    client: AsyncClient, headers: dict, exp_id: int,
    name: str = "M1", version_no: str = "v1.0.0",
) -> int:
    r = await client.post(
        "/api/v1/model-versions",
        json={"experiment_id": exp_id, "name": name, "version_no": version_no},
        headers=headers,
    )
    return r.json()["id"]


# ── FR-1103 测试用例 ──────────────────────────────────────────────


async def test_link_dataset_version_sets_in_use(client, db):
    """FR-1103 关联数据集版本时自动设置 in_use。"""
    session, project_id, dv_id = db
    headers = await _login(client)
    exp_id = await _create_experiment(client, headers, project_id)

    r = await client.post(
        f"/api/v1/training-experiments/{exp_id}/dataset-versions",
        json={"dataset_version_id": dv_id},
        headers=headers,
    )
    assert r.status_code == 200

    stmt = select(DatasetVersion).where(DatasetVersion.id == dv_id)
    result = await session.execute(stmt)
    assert result.scalar_one().status == "in_use"


async def test_unlink_restores_ready_when_no_other_experiment(client, db):
    """FR-1103 解除关联后无其他引用则恢复 ready。"""
    session, project_id, dv_id = db
    headers = await _login(client)
    exp_id = await _create_experiment(client, headers, project_id)

    await client.post(
        f"/api/v1/training-experiments/{exp_id}/dataset-versions",
        json={"dataset_version_id": dv_id},
        headers=headers,
    )

    r = await client.delete(
        f"/api/v1/training-experiments/{exp_id}/dataset-versions/{dv_id}",
        headers=headers,
    )
    assert r.status_code == 200

    stmt = select(DatasetVersion).where(DatasetVersion.id == dv_id)
    result = await session.execute(stmt)
    assert result.scalar_one().status == "ready"


async def test_experiment_frozen_fields_after_link(client, db):
    """FR-1103 关联数据集版本后实验冻结字段不可修改。"""
    _, project_id, dv_id = db
    headers = await _login(client)
    exp_id = await _create_experiment(client, headers, project_id)

    await client.post(
        f"/api/v1/training-experiments/{exp_id}/dataset-versions",
        json={"dataset_version_id": dv_id},
        headers=headers,
    )

    r = await client.put(
        f"/api/v1/training-experiments/{exp_id}",
        json={"framework": "tensorflow"},
        headers=headers,
    )
    assert r.status_code == 409


async def test_experiment_mutable_fields_after_link(client, db):
    """FR-1103 关联后 name/description/metrics 等仍可修改。"""
    _, project_id, dv_id = db
    headers = await _login(client)
    exp_id = await _create_experiment(client, headers, project_id)

    await client.post(
        f"/api/v1/training-experiments/{exp_id}/dataset-versions",
        json={"dataset_version_id": dv_id},
        headers=headers,
    )

    r = await client.put(
        f"/api/v1/training-experiments/{exp_id}",
        json={"name": "新名称", "metrics": '{"accuracy": 0.95}'},
        headers=headers,
    )
    assert r.status_code == 200


async def test_experiment_with_model_cannot_delete(client, db):
    """FR-1103 有关联模型版本时不可删除实验。"""
    _, project_id, dv_id = db
    headers = await _login(client)
    exp_id = await _create_experiment(client, headers, project_id)
    await _create_model_version(client, headers, exp_id)

    r = await client.delete(
        f"/api/v1/training-experiments/{exp_id}",
        headers=headers,
    )
    assert r.status_code == 409


async def test_model_version_no_format_validated(client, db):
    """FR-1103 模型版本号格式校验。"""
    _, project_id, _ = db
    headers = await _login(client)
    exp_id = await _create_experiment(client, headers, project_id)

    r = await client.post(
        "/api/v1/model-versions",
        json={"experiment_id": exp_id, "name": "M1", "version_no": "1.0"},
        headers=headers,
    )
    assert r.status_code == 422


async def test_model_frozen_fields_when_ready(client, db):
    """FR-1103 ready 状态下模型版本冻结字段不可修改。"""
    _, project_id, _ = db
    headers = await _login(client)
    exp_id = await _create_experiment(client, headers, project_id)
    mv_id = await _create_model_version(client, headers, exp_id)

    await client.patch(f"/api/v1/model-versions/{mv_id}/ready", headers=headers)

    r = await client.put(
        f"/api/v1/model-versions/{mv_id}",
        json={"name": "新名称"},
        headers=headers,
    )
    assert r.status_code == 409


async def test_model_notes_mutable_when_frozen(client, db):
    """FR-1103 notes 在冻结状态下仍可修改。"""
    _, project_id, _ = db
    headers = await _login(client)
    exp_id = await _create_experiment(client, headers, project_id)
    mv_id = await _create_model_version(client, headers, exp_id)

    await client.patch(f"/api/v1/model-versions/{mv_id}/ready", headers=headers)

    r = await client.put(
        f"/api/v1/model-versions/{mv_id}",
        json={"notes": "新备注"},
        headers=headers,
    )
    assert r.status_code == 200


async def test_delivered_model_cannot_delete(client, db):
    """FR-1103 delivered 模型不可删除。"""
    session, project_id, _ = db
    headers = await _login(client)
    exp_id = await _create_experiment(client, headers, project_id)
    mv_id = await _create_model_version(client, headers, exp_id)

    stmt = select(ModelVersion).where(ModelVersion.id == mv_id)
    result = await session.execute(stmt)
    mv = result.scalar_one()
    mv.status = "delivered"
    await session.commit()

    r = await client.delete(f"/api/v1/model-versions/{mv_id}", headers=headers)
    assert r.status_code == 409


async def test_get_experiment_traceability(client, db):
    """FR-1103 实验可追溯性查询。"""
    _, project_id, dv_id = db
    headers = await _login(client)
    exp_id = await _create_experiment(client, headers, project_id)

    await client.post(
        f"/api/v1/training-experiments/{exp_id}/dataset-versions",
        json={"dataset_version_id": dv_id},
        headers=headers,
    )
    await _create_model_version(client, headers, exp_id)

    r = await client.get(
        f"/api/v1/training-experiments/{exp_id}/traceability",
        headers=headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert "experiment" in data
    assert len(data["dataset_versions"]) == 1
    assert len(data["model_versions"]) == 1


async def test_get_model_version_traceability(client, db):
    """FR-1103 模型版本可追溯性查询。"""
    _, project_id, dv_id = db
    headers = await _login(client)
    exp_id = await _create_experiment(client, headers, project_id)

    await client.post(
        f"/api/v1/training-experiments/{exp_id}/dataset-versions",
        json={"dataset_version_id": dv_id},
        headers=headers,
    )
    mv_id = await _create_model_version(client, headers, exp_id)

    r = await client.get(
        f"/api/v1/model-versions/{mv_id}/traceability",
        headers=headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert "model_version" in data
    assert "experiment_id" in data
    assert len(data["dataset_versions"]) == 1
