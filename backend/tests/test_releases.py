"""FR-504 版本/发布记录测试——严格对应 prd1_5.md 簇 E 测试用例清单"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from datetime import date

from app.main import app
from app.database import get_db
from app.models.base import Base
from app.models.user import User
from app.models.customer import Customer
from app.models.project import Project
from app.core.security import get_password_hash

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


async def _login(client: AsyncClient) -> dict:
    r = await client.post("/api/v1/auth/login", data={"username": "admin", "password": "admin123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _url(project_id: int, suffix: str = "") -> str:
    return f"/api/v1/projects/{project_id}/releases{suffix}"


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


def _make_release(version: str = "v1.0.0", is_online: bool = False) -> dict:
    return {
        "version_no": version,
        "release_date": "2026-04-07",
        "release_type": "release",
        "is_current_online": is_online,
        "changelog": "初始版本发布",
    }


async def test_create_release_as_current_online(client, db):
    """test_create_release_as_current_online → FR-504"""
    _, project_id = db
    h = await _login(client)
    r = await client.post(_url(project_id), json=_make_release("v1.0.0", True), headers=h)
    assert r.status_code == 201
    assert r.json()["is_current_online"] is True


async def test_create_release_clears_previous_online(client, db):
    """test_create_release_clears_previous_online → FR-504"""
    _, project_id = db
    h = await _login(client)
    r1 = await client.post(_url(project_id), json=_make_release("v1.0.0", True), headers=h)
    assert r1.status_code == 201
    r2 = await client.post(_url(project_id), json=_make_release("v2.0.0", True), headers=h)
    assert r2.status_code == 201
    # v1 不再 online
    detail_v1 = await client.get(_url(project_id, f"/{r1.json()['id']}"), headers=h)
    assert detail_v1.json()["is_current_online"] is False
    # v2 是 online
    assert r2.json()["is_current_online"] is True


async def test_create_release_no_two_current_online(client, db):
    """test_create_release_no_two_current_online → FR-504（唯一性）"""
    _, project_id = db
    h = await _login(client)
    await client.post(_url(project_id), json=_make_release("v1.0.0", True), headers=h)
    await client.post(_url(project_id), json=_make_release("v2.0.0", True), headers=h)
    await client.post(_url(project_id), json=_make_release("v3.0.0", True), headers=h)
    r = await client.get(_url(project_id), headers=h)
    online_count = sum(1 for i in r.json() if i["is_current_online"])
    assert online_count == 1


async def test_set_online_clears_other_versions(client, db):
    """test_set_online_clears_other_versions → FR-504"""
    _, project_id = db
    h = await _login(client)
    r1 = await client.post(_url(project_id), json=_make_release("v1.0.0", True), headers=h)
    r2 = await client.post(_url(project_id), json=_make_release("v2.0.0"), headers=h)
    id1, id2 = r1.json()["id"], r2.json()["id"]
    # 设置 v2 为 online
    resp = await client.post(_url(project_id, f"/{id2}/set-online"), headers=h)
    assert resp.status_code == 200
    assert resp.json()["is_current_online"] is True
    # v1 不再 online
    detail = await client.get(_url(project_id, f"/{id1}"), headers=h)
    assert detail.json()["is_current_online"] is False


async def test_set_online_no_two_current_online(client, db):
    """test_set_online_no_two_current_online → FR-504（唯一性）"""
    _, project_id = db
    h = await _login(client)
    r1 = await client.post(_url(project_id), json=_make_release("v1.0.0", True), headers=h)
    r2 = await client.post(_url(project_id), json=_make_release("v2.0.0"), headers=h)
    r3 = await client.post(_url(project_id), json=_make_release("v3.0.0"), headers=h)
    await client.post(_url(project_id, f"/{r1.json()['id']}/set-online"), headers=h)
    items = (await client.get(_url(project_id), headers=h)).json()
    online_count = sum(1 for i in items if i["is_current_online"])
    assert online_count == 1


async def test_get_releases_ordered_by_date_desc(client, db):
    """test_get_releases_ordered_by_date_desc → FR-504"""
    _, project_id = db
    h = await _login(client)
    await client.post(_url(project_id), json={**_make_release(), "release_date": "2026-01-01"}, headers=h)
    await client.post(_url(project_id), json={**_make_release(), "release_date": "2026-03-01"}, headers=h)
    await client.post(_url(project_id), json={**_make_release(), "release_date": "2026-02-01"}, headers=h)
    r = await client.get(_url(project_id), headers=h)
    items = r.json()
    assert items[0]["release_date"] == "2026-03-01"
    assert items[2]["release_date"] == "2026-01-01"


async def test_get_releases_current_online_has_is_pinned_true(client, db):
    """test_get_releases_current_online_has_is_pinned_true → FR-504"""
    _, project_id = db
    h = await _login(client)
    await client.post(_url(project_id), json=_make_release("v1.0.0", True), headers=h)
    await client.post(_url(project_id), json=_make_release("v2.0.0"), headers=h)
    r = await client.get(_url(project_id), headers=h)
    items = r.json()
    pinned = [i for i in items if i["is_pinned"]]
    assert len(pinned) == 1
    assert pinned[0]["version_no"] == "v1.0.0"


async def test_delete_release_returns_405(client, db):
    """test_delete_release_returns_405 → FR-504"""
    _, project_id = db
    h = await _login(client)
    r = await client.post(_url(project_id), json=_make_release(), headers=h)
    resp = await client.delete(_url(project_id, f"/{r.json()['id']}"), headers=h)
    assert resp.status_code == 405


async def test_put_version_no_rejected(client, db):
    """test_put_version_no_rejected → FR-504"""
    _, project_id = db
    h = await _login(client)
    r = await client.post(_url(project_id), json=_make_release(), headers=h)
    rel_id = r.json()["id"]
    resp = await client.put(_url(project_id, f"/{rel_id}"), json={"version_no": "v9.9.9"}, headers=h)
    assert resp.status_code == 422
    assert "版本号和发布日期不可修改" in resp.json()["detail"]


async def test_put_release_date_rejected(client, db):
    """test_put_release_date_rejected → FR-504"""
    _, project_id = db
    h = await _login(client)
    r = await client.post(_url(project_id), json=_make_release(), headers=h)
    rel_id = r.json()["id"]
    resp = await client.put(_url(project_id, f"/{rel_id}"), json={"release_date": "2099-01-01"}, headers=h)
    assert resp.status_code == 422


async def test_patch_version_no_rejected(client, db):
    """test_patch_version_no_rejected → FR-504（PATCH 同样约束）"""
    _, project_id = db
    h = await _login(client)
    r = await client.post(_url(project_id), json=_make_release(), headers=h)
    rel_id = r.json()["id"]
    resp = await client.patch(_url(project_id, f"/{rel_id}"), json={"version_no": "v9.9.9"}, headers=h)
    assert resp.status_code == 422


async def test_patch_changelog_success(client, db):
    """test_patch_changelog_success → FR-504"""
    _, project_id = db
    h = await _login(client)
    r = await client.post(_url(project_id), json=_make_release(), headers=h)
    rel_id = r.json()["id"]
    resp = await client.patch(_url(project_id, f"/{rel_id}"), json={"changelog": "更新日志"}, headers=h)
    assert resp.status_code == 200
    assert resp.json()["changelog"] == "更新日志"


async def test_project_detail_includes_current_version(client, db):
    """test_project_detail_includes_current_version → FR-504"""
    _, project_id = db
    h = await _login(client)
    await client.post(_url(project_id), json=_make_release("v1.2.0", True), headers=h)
    r = await client.get(f"/api/v1/projects/{project_id}", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert data["current_version"] == "v1.2.0"


async def test_project_detail_current_version_null_when_none(client, db):
    """test_project_detail_current_version_null_when_none → FR-504"""
    _, project_id = db
    h = await _login(client)
    r = await client.get(f"/api/v1/projects/{project_id}", headers=h)
    assert r.status_code == 200
    assert r.json()["current_version"] is None
