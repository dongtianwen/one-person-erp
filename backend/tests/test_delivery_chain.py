"""FR-1105 端到端交付链路测试——数据集→标注→实验→模型→交付→验收。"""
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
from app.models.delivery_package import DeliveryPackage
from app.models.acceptance import Acceptance
from app.models.requirement import Requirement
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
        proj = Project(name="链路测试项目", customer_id=cust.id)
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


async def test_full_chain_dataset_to_acceptance(client, db):
    """FR-1105 完整交付链路：数据集→标注→实验→模型→交付→验收。"""
    session, project_id = db
    headers = await _login(client)

    # 1. 创建数据集 + 版本(draft)
    r = await client.post("/api/v1/datasets", json={"project_id": project_id, "name": "链路数据集"}, headers=headers)
    ds_id = r.json()["id"]

    r = await client.post(f"/api/v1/datasets/{ds_id}/versions", json={"version_no": "v1.0", "sample_count": 500}, headers=headers)
    dv_id = r.json()["id"]

    # 2. ready
    await client.patch(f"/api/v1/datasets/versions/{dv_id}/ready", headers=headers)

    # 3. 创建标注任务 + 完成
    r = await client.post("/api/v1/annotation-tasks", json={"project_id": project_id, "dataset_version_id": dv_id, "name": "标注任务1"}, headers=headers)
    task_id = r.json()["id"]

    await client.patch(f"/api/v1/annotation-tasks/{task_id}/status", json={"status": "in_progress"}, headers=headers)
    await client.patch(f"/api/v1/annotation-tasks/{task_id}/status", json={"status": "quality_check"}, headers=headers)
    await client.patch(f"/api/v1/annotation-tasks/{task_id}/status", json={"status": "completed"}, headers=headers)

    # 4. 创建训练实验 + 关联数据集版本（自动 in_use）
    r = await client.post("/api/v1/training-experiments", json={"project_id": project_id, "name": "链路实验", "framework": "pytorch"}, headers=headers)
    exp_id = r.json()["id"]

    r = await client.post(f"/api/v1/training-experiments/{exp_id}/dataset-versions", json={"dataset_version_id": dv_id}, headers=headers)
    assert r.status_code == 200

    # 验证 in_use
    stmt = select(DatasetVersion).where(DatasetVersion.id == dv_id)
    result = await session.execute(stmt)
    assert result.scalar_one().status == "in_use"

    # 5. 创建模型版本(training)→ready
    r = await client.post("/api/v1/model-versions", json={"experiment_id": exp_id, "name": "链路模型", "version_no": "v1.0.0"}, headers=headers)
    mv_id = r.json()["id"]

    await client.patch(f"/api/v1/model-versions/{mv_id}/ready", headers=headers)

    # 6. 创建交付包 + 关联模型 → ready → deliver（模型自动 delivered）
    r = await client.post("/api/v1/delivery-packages", json={"project_id": project_id, "name": "链路交付包"}, headers=headers)
    pkg_id = r.json()["id"]

    await client.post(f"/api/v1/delivery-packages/{pkg_id}/model-versions", json={"model_version_id": mv_id}, headers=headers)
    await client.patch(f"/api/v1/delivery-packages/{pkg_id}/ready", headers=headers)
    await client.patch(f"/api/v1/delivery-packages/{pkg_id}/deliver", headers=headers)

    # 验证模型版本 delivered
    stmt = select(ModelVersion).where(ModelVersion.id == mv_id)
    result = await session.execute(stmt)
    assert result.scalar_one().status == "delivered"

    # 7. 验收(passed) → 交付包自动 accepted
    r = await client.post(
        f"/api/v1/delivery-packages/{pkg_id}/acceptance",
        json={"result": "passed", "delivery_package_id": pkg_id},
        headers=headers,
    )
    assert r.status_code == 200

    stmt = select(DeliveryPackage).where(DeliveryPackage.id == pkg_id)
    result = await session.execute(stmt)
    assert result.scalar_one().status == "accepted"


async def test_traceability_model_to_dataset(client, db):
    """FR-1105 模型→数据集追溯。"""
    session, project_id = db
    headers = await _login(client)

    r = await client.post("/api/v1/datasets", json={"project_id": project_id, "name": "追溯数据集"}, headers=headers)
    ds_id = r.json()["id"]
    r = await client.post(f"/api/v1/datasets/{ds_id}/versions", json={"version_no": "v1.0"}, headers=headers)
    dv_id = r.json()["id"]
    await client.patch(f"/api/v1/datasets/versions/{dv_id}/ready", headers=headers)

    r = await client.post("/api/v1/training-experiments", json={"project_id": project_id, "name": "追溯实验"}, headers=headers)
    exp_id = r.json()["id"]
    await client.post(f"/api/v1/training-experiments/{exp_id}/dataset-versions", json={"dataset_version_id": dv_id}, headers=headers)

    r = await client.post("/api/v1/model-versions", json={"experiment_id": exp_id, "name": "追溯模型", "version_no": "v1.0.0"}, headers=headers)
    mv_id = r.json()["id"]

    r = await client.get(f"/api/v1/model-versions/{mv_id}/traceability", headers=headers)
    data = r.json()
    assert len(data["dataset_versions"]) == 1
    assert data["dataset_versions"][0]["version_no"] == "v1.0"


async def test_traceability_package_to_dataset(client, db):
    """FR-1105 交付包→数据集追溯。"""
    session, project_id = db
    headers = await _login(client)

    r = await client.post("/api/v1/datasets", json={"project_id": project_id, "name": "包追溯数据集"}, headers=headers)
    ds_id = r.json()["id"]
    r = await client.post(f"/api/v1/datasets/{ds_id}/versions", json={"version_no": "v1.0"}, headers=headers)
    dv_id = r.json()["id"]
    await client.patch(f"/api/v1/datasets/versions/{dv_id}/ready", headers=headers)

    r = await client.post("/api/v1/training-experiments", json={"project_id": project_id, "name": "包追溯实验"}, headers=headers)
    exp_id = r.json()["id"]
    await client.post(f"/api/v1/training-experiments/{exp_id}/dataset-versions", json={"dataset_version_id": dv_id}, headers=headers)

    r = await client.post("/api/v1/model-versions", json={"experiment_id": exp_id, "name": "包追溯模型", "version_no": "v1.0.0"}, headers=headers)
    mv_id = r.json()["id"]
    await client.patch(f"/api/v1/model-versions/{mv_id}/ready", headers=headers)

    r = await client.post("/api/v1/delivery-packages", json={"project_id": project_id, "name": "追溯包"}, headers=headers)
    pkg_id = r.json()["id"]

    await client.post(f"/api/v1/delivery-packages/{pkg_id}/model-versions", json={"model_version_id": mv_id}, headers=headers)
    await client.patch(f"/api/v1/delivery-packages/{pkg_id}/ready", headers=headers)
    await client.patch(f"/api/v1/delivery-packages/{pkg_id}/deliver", headers=headers)
    await client.post(f"/api/v1/delivery-packages/{pkg_id}/acceptance", json={"result": "passed", "delivery_package_id": pkg_id}, headers=headers)

    r = await client.get(f"/api/v1/delivery-packages/{pkg_id}/traceability", headers=headers)
    data = r.json()["data"]
    assert len(data["model_versions"]) == 1
    assert len(data["model_versions"][0]["dataset_versions"]) == 1
    assert data["acceptance"] is not None


async def test_acceptance_not_orphan(client, db):
    """FR-1105 验收记录有 delivery_package_id，不孤立。"""
    session, project_id = db
    headers = await _login(client)

    r = await client.post("/api/v1/datasets", json={"project_id": project_id, "name": "孤立数据集"}, headers=headers)
    ds_id = r.json()["id"]
    r = await client.post(f"/api/v1/datasets/{ds_id}/versions", json={"version_no": "v1.0"}, headers=headers)
    dv_id = r.json()["id"]
    await client.patch(f"/api/v1/datasets/versions/{dv_id}/ready", headers=headers)

    r = await client.post("/api/v1/training-experiments", json={"project_id": project_id, "name": "孤立实验"}, headers=headers)
    exp_id = r.json()["id"]
    r = await client.post("/api/v1/model-versions", json={"experiment_id": exp_id, "name": "孤立模型", "version_no": "v1.0.0"}, headers=headers)
    mv_id = r.json()["id"]
    await client.patch(f"/api/v1/model-versions/{mv_id}/ready", headers=headers)

    r = await client.post("/api/v1/delivery-packages", json={"project_id": project_id, "name": "孤立包"}, headers=headers)
    pkg_id = r.json()["id"]

    await client.post(f"/api/v1/delivery-packages/{pkg_id}/model-versions", json={"model_version_id": mv_id}, headers=headers)
    await client.patch(f"/api/v1/delivery-packages/{pkg_id}/ready", headers=headers)
    await client.patch(f"/api/v1/delivery-packages/{pkg_id}/deliver", headers=headers)
    await client.post(f"/api/v1/delivery-packages/{pkg_id}/acceptance", json={"result": "passed", "delivery_package_id": pkg_id}, headers=headers)

    stmt = select(Acceptance).where(Acceptance.delivery_package_id == pkg_id)
    result = await session.execute(stmt)
    acc = result.scalar_one()
    assert acc.delivery_package_id == pkg_id
    assert acc.acceptance_type == "model"


async def test_frozen_fields_protected_in_chain(client, db):
    """FR-1105 冻结字段在整条链路中被保护。"""
    _, project_id = db
    headers = await _login(client)

    # 数据集版本 ready 后冻结
    r = await client.post("/api/v1/datasets", json={"project_id": project_id, "name": "冻结数据集"}, headers=headers)
    ds_id = r.json()["id"]
    r = await client.post(f"/api/v1/datasets/{ds_id}/versions", json={"version_no": "v1.0", "sample_count": 100}, headers=headers)
    dv_id = r.json()["id"]
    await client.patch(f"/api/v1/datasets/versions/{dv_id}/ready", headers=headers)

    r = await client.put(f"/api/v1/datasets/versions/{dv_id}", json={"sample_count": 200}, headers=headers)
    assert r.status_code == 409

    # 模型版本 ready 后冻结
    r = await client.post("/api/v1/training-experiments", json={"project_id": project_id, "name": "冻结实验"}, headers=headers)
    exp_id = r.json()["id"]
    r = await client.post("/api/v1/model-versions", json={"experiment_id": exp_id, "name": "冻结模型", "version_no": "v1.0.0"}, headers=headers)
    mv_id = r.json()["id"]
    await client.patch(f"/api/v1/model-versions/{mv_id}/ready", headers=headers)

    r = await client.put(f"/api/v1/model-versions/{mv_id}", json={"name": "新名称"}, headers=headers)
    assert r.status_code == 409

    # 实验关联数据集后冻结
    r = await client.post("/api/v1/datasets", json={"project_id": project_id, "name": "冻结数据集2"}, headers=headers)
    ds2_id = r.json()["id"]
    r = await client.post(f"/api/v1/datasets/{ds2_id}/versions", json={"version_no": "v1.0"}, headers=headers)
    dv2_id = r.json()["id"]
    await client.patch(f"/api/v1/datasets/versions/{dv2_id}/ready", headers=headers)

    r = await client.post(f"/api/v1/training-experiments/{exp_id}/dataset-versions", json={"dataset_version_id": dv2_id}, headers=headers)
    assert r.status_code == 200

    r = await client.put(f"/api/v1/training-experiments/{exp_id}", json={"framework": "tensorflow"}, headers=headers)
    assert r.status_code == 409
