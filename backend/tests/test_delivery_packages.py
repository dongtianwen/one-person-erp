"""FR-1104 交付包与验收测试——覆盖 ready 前置、deliver 原子性、验收规则、删除保护。"""
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
        exp = TrainingExperiment(project_id=proj.id, name="EXP1")
        session.add(exp)
        await session.commit()
        mv = ModelVersion(
            project_id=proj.id, experiment_id=exp.id,
            name="M1", version_no="v1.0.0", status="ready",
        )
        session.add(mv)
        await session.commit()
        yield session, proj.id, dv.id, mv.id, exp.id
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def client(db):
    session, _, _, _, _ = db
    async def override_get_db():
        yield session
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


async def _create_package(client: AsyncClient, headers: dict, project_id: int) -> int:
    r = await client.post(
        "/api/v1/delivery-packages",
        json={"project_id": project_id, "name": "交付包1"},
        headers=headers,
    )
    return r.json()["id"]


# ── FR-1104 测试用例 ──────────────────────────────────────────────


async def test_ready_requires_content(client, db):
    """FR-1104 空包不能标记为 ready。"""
    _, project_id, _, _, _ = db
    headers = await _login(client)
    pkg_id = await _create_package(client, headers, project_id)

    r = await client.patch(f"/api/v1/delivery-packages/{pkg_id}/ready", headers=headers)
    assert r.status_code == 422


async def test_deliver_updates_model_versions(client, db):
    """FR-1104 deliver 原子更新模型版本状态为 delivered。"""
    session, project_id, _, mv_id, _ = db
    headers = await _login(client)
    pkg_id = await _create_package(client, headers, project_id)

    # 关联模型版本
    await client.post(
        f"/api/v1/delivery-packages/{pkg_id}/model-versions",
        json={"model_version_id": mv_id},
        headers=headers,
    )
    # ready
    await client.patch(f"/api/v1/delivery-packages/{pkg_id}/ready", headers=headers)
    # deliver
    r = await client.patch(f"/api/v1/delivery-packages/{pkg_id}/deliver", headers=headers)
    assert r.status_code == 200

    # 验证模型版本状态
    stmt = select(ModelVersion).where(ModelVersion.id == mv_id)
    result = await session.execute(stmt)
    assert result.scalar_one().status == "delivered"


async def test_deliver_is_atomic(client, db):
    """FR-1104 deliver 设置 delivered_at。"""
    session, project_id, _, mv_id, _ = db
    headers = await _login(client)
    pkg_id = await _create_package(client, headers, project_id)

    await client.post(
        f"/api/v1/delivery-packages/{pkg_id}/model-versions",
        json={"model_version_id": mv_id},
        headers=headers,
    )
    await client.patch(f"/api/v1/delivery-packages/{pkg_id}/ready", headers=headers)
    await client.patch(f"/api/v1/delivery-packages/{pkg_id}/deliver", headers=headers)

    stmt = select(DeliveryPackage).where(DeliveryPackage.id == pkg_id)
    result = await session.execute(stmt)
    pkg = result.scalar_one()
    assert pkg.status == "delivered"
    assert pkg.delivered_at is not None


async def test_acceptance_requires_delivery_package_id(client, db):
    """FR-1104 验收必须提供 delivery_package_id。"""
    _, project_id, _, _, _ = db
    headers = await _login(client)
    pkg_id = await _create_package(client, headers, project_id)

    r = await client.post(
        f"/api/v1/delivery-packages/{pkg_id}/acceptance",
        json={"result": "passed"},
        headers=headers,
    )
    assert r.status_code == 422


async def test_acceptance_package_id_matches_current(client, db):
    """FR-1104 delivery_package_id 必须匹配当前包。"""
    _, project_id, _, _, _ = db
    headers = await _login(client)
    pkg_id = await _create_package(client, headers, project_id)

    r = await client.post(
        f"/api/v1/delivery-packages/{pkg_id}/acceptance",
        json={"result": "passed", "delivery_package_id": 99999},
        headers=headers,
    )
    assert r.status_code == 422


async def test_acceptance_type_auto_determined(client, db):
    """FR-1104 验收类型根据包内容自动判断。"""
    session, project_id, _, mv_id, _ = db
    headers = await _login(client)
    pkg_id = await _create_package(client, headers, project_id)

    await client.post(
        f"/api/v1/delivery-packages/{pkg_id}/model-versions",
        json={"model_version_id": mv_id},
        headers=headers,
    )
    await client.patch(f"/api/v1/delivery-packages/{pkg_id}/ready", headers=headers)
    await client.patch(f"/api/v1/delivery-packages/{pkg_id}/deliver", headers=headers)

    r = await client.post(
        f"/api/v1/delivery-packages/{pkg_id}/acceptance",
        json={"result": "passed", "delivery_package_id": pkg_id},
        headers=headers,
    )
    assert r.status_code == 200
    assert r.json()["acceptance_type"] == "model"


async def test_acceptance_passed_transitions_package_accepted(client, db):
    """FR-1104 passed 验收原子更新包状态为 accepted。"""
    session, project_id, _, mv_id, _ = db
    headers = await _login(client)
    pkg_id = await _create_package(client, headers, project_id)

    await client.post(
        f"/api/v1/delivery-packages/{pkg_id}/model-versions",
        json={"model_version_id": mv_id},
        headers=headers,
    )
    await client.patch(f"/api/v1/delivery-packages/{pkg_id}/ready", headers=headers)
    await client.patch(f"/api/v1/delivery-packages/{pkg_id}/deliver", headers=headers)

    await client.post(
        f"/api/v1/delivery-packages/{pkg_id}/acceptance",
        json={"result": "passed", "delivery_package_id": pkg_id},
        headers=headers,
    )

    stmt = select(DeliveryPackage).where(DeliveryPackage.id == pkg_id)
    result = await session.execute(stmt)
    assert result.scalar_one().status == "accepted"


async def test_package_only_one_acceptance(client, db):
    """FR-1104 一个交付包只能有一条验收记录。"""
    _, project_id, _, mv_id, _ = db
    headers = await _login(client)
    pkg_id = await _create_package(client, headers, project_id)

    await client.post(
        f"/api/v1/delivery-packages/{pkg_id}/model-versions",
        json={"model_version_id": mv_id},
        headers=headers,
    )
    await client.patch(f"/api/v1/delivery-packages/{pkg_id}/ready", headers=headers)
    await client.patch(f"/api/v1/delivery-packages/{pkg_id}/deliver", headers=headers)

    await client.post(
        f"/api/v1/delivery-packages/{pkg_id}/acceptance",
        json={"result": "passed", "delivery_package_id": pkg_id},
        headers=headers,
    )

    r = await client.post(
        f"/api/v1/delivery-packages/{pkg_id}/acceptance",
        json={"result": "failed", "delivery_package_id": pkg_id},
        headers=headers,
    )
    assert r.status_code == 409


async def test_accepted_package_cannot_delete(client, db):
    """FR-1104 accepted 包不可删除。"""
    session, project_id, _, mv_id, _ = db
    headers = await _login(client)
    pkg_id = await _create_package(client, headers, project_id)

    await client.post(
        f"/api/v1/delivery-packages/{pkg_id}/model-versions",
        json={"model_version_id": mv_id},
        headers=headers,
    )
    await client.patch(f"/api/v1/delivery-packages/{pkg_id}/ready", headers=headers)
    await client.patch(f"/api/v1/delivery-packages/{pkg_id}/deliver", headers=headers)
    await client.post(
        f"/api/v1/delivery-packages/{pkg_id}/acceptance",
        json={"result": "passed", "delivery_package_id": pkg_id},
        headers=headers,
    )

    r = await client.delete(f"/api/v1/delivery-packages/{pkg_id}", headers=headers)
    assert r.status_code == 409


async def test_get_package_traceability_complete(client, db):
    """FR-1104 完整追溯链。"""
    _, project_id, dv_id, mv_id, _ = db
    headers = await _login(client)
    pkg_id = await _create_package(client, headers, project_id)

    await client.post(
        f"/api/v1/delivery-packages/{pkg_id}/model-versions",
        json={"model_version_id": mv_id},
        headers=headers,
    )
    await client.post(
        f"/api/v1/delivery-packages/{pkg_id}/dataset-versions",
        json={"dataset_version_id": dv_id},
        headers=headers,
    )
    await client.patch(f"/api/v1/delivery-packages/{pkg_id}/ready", headers=headers)
    await client.patch(f"/api/v1/delivery-packages/{pkg_id}/deliver", headers=headers)
    await client.post(
        f"/api/v1/delivery-packages/{pkg_id}/acceptance",
        json={"result": "passed", "delivery_package_id": pkg_id},
        headers=headers,
    )

    r = await client.get(
        f"/api/v1/delivery-packages/{pkg_id}/traceability",
        headers=headers,
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert "package" in data
    assert "model_versions" in data
    assert "dataset_versions" in data
    assert "acceptance" in data
    assert data["acceptance"] is not None
    assert data["acceptance"]["result"] == "passed"
