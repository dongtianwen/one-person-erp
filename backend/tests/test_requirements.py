"""FR-501 需求与变更管理测试——严格对应 prd1_5.md 簇 B 测试用例清单"""
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
from app.models.requirement import Requirement, RequirementChange
from app.models.change_order import ChangeOrder
from app.models.contract import Contract
from app.core.security import get_password_hash
from app.core.requirement_utils import can_modify_field

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _login(client: AsyncClient) -> dict:
    r = await client.post("/api/v1/auth/login", data={"username": "admin", "password": "admin123"})
    return _auth_header(r.json()["access_token"])


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


def _url(project_id: int, suffix: str = "") -> str:
    return f"/api/v1/projects/{project_id}/requirements{suffix}"


# ── 独立函数测试 ──────────────────────────────────────────────


def test_can_modify_field_pending_allows_all():
    assert can_modify_field("pending", "summary") is True
    assert can_modify_field("pending", "version_no") is True
    assert can_modify_field("pending", "notes") is True


def test_can_modify_field_confirmed_blocks_summary_and_version():
    assert can_modify_field("confirmed", "summary") is False
    assert can_modify_field("confirmed", "version_no") is False
    assert can_modify_field("confirmed", "notes") is True
    assert can_modify_field("confirmed", "confirm_method") is True


# ── API 接口测试 ─────────────────────────────────────────────


async def test_create_requirement_sets_as_current(client, db):
    """test_create_requirement_sets_as_current → FR-501"""
    _, project_id = db
    h = await _login(client)
    r = await client.post(_url(project_id), json={"version_no": "v1.0", "summary": "初始需求"}, headers=h)
    assert r.status_code == 201
    assert r.json()["is_current"] is True


async def test_create_requirement_clears_previous_current(client, db):
    """test_create_requirement_clears_previous_current → FR-501"""
    _, project_id = db
    h = await _login(client)
    r1 = await client.post(_url(project_id), json={"version_no": "v1.0", "summary": "第一版"}, headers=h)
    assert r1.status_code == 201
    r2 = await client.post(_url(project_id), json={"version_no": "v2.0", "summary": "第二版"}, headers=h)
    assert r2.status_code == 201
    # v1 不再是 current
    detail_v1 = await client.get(_url(project_id, f"/{r1.json()['id']}"), headers=h)
    assert detail_v1.json()["is_current"] is False
    # v2 是 current
    assert r2.json()["is_current"] is True


async def test_create_requirement_no_two_current_after_create(client, db):
    """test_create_requirement_no_two_current_after_create → FR-501（唯一性）"""
    _, project_id = db
    h = await _login(client)
    await client.post(_url(project_id), json={"version_no": "v1.0", "summary": "第一版"}, headers=h)
    await client.post(_url(project_id), json={"version_no": "v2.0", "summary": "第二版"}, headers=h)
    await client.post(_url(project_id), json={"version_no": "v3.0", "summary": "第三版"}, headers=h)
    r = await client.get(_url(project_id), headers=h)
    items = r.json()
    current_count = sum(1 for i in items if i["is_current"])
    assert current_count == 1


async def test_get_requirements_list_ordered_by_created_desc(client, db):
    """test_get_requirements_list_ordered_by_created_desc → FR-501"""
    _, project_id = db
    h = await _login(client)
    await client.post(_url(project_id), json={"version_no": "v1.0", "summary": "第一版"}, headers=h)
    await client.post(_url(project_id), json={"version_no": "v2.0", "summary": "第二版"}, headers=h)
    r = await client.get(_url(project_id), headers=h)
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 2
    assert items[0]["version_no"] == "v2.0"
    assert items[1]["version_no"] == "v1.0"


async def test_get_requirement_detail_includes_changes(client, db):
    """test_get_requirement_detail_includes_changes → FR-501"""
    _, project_id = db
    h = await _login(client)
    r = await client.post(_url(project_id), json={"version_no": "v1.0", "summary": "初始需求"}, headers=h)
    req_id = r.json()["id"]
    # 添加变更记录
    await client.post(
        _url(project_id, f"/{req_id}/changes"),
        json={"title": "新增功能", "description": "用户登录", "change_type": "add", "is_billable": False, "initiated_by": "customer"},
        headers=h,
    )
    detail = await client.get(_url(project_id, f"/{req_id}"), headers=h)
    assert detail.status_code == 200
    data = detail.json()
    assert "changes" in data
    assert len(data["changes"]) == 1
    assert data["changes"][0]["title"] == "新增功能"


async def test_put_pending_requirement_summary_success(client, db):
    """test_put_pending_requirement_summary_success → FR-501"""
    _, project_id = db
    h = await _login(client)
    r = await client.post(_url(project_id), json={"version_no": "v1.0", "summary": "旧内容"}, headers=h)
    req_id = r.json()["id"]
    resp = await client.put(_url(project_id, f"/{req_id}"), json={"summary": "新内容"}, headers=h)
    assert resp.status_code == 200
    assert resp.json()["summary"] == "新内容"


async def test_put_confirmed_requirement_summary_rejected(client, db):
    """test_put_confirmed_requirement_summary_rejected → FR-501"""
    _, project_id = db
    h = await _login(client)
    r = await client.post(_url(project_id), json={"version_no": "v1.0", "summary": "内容"}, headers=h)
    req_id = r.json()["id"]
    # 先设置为 confirmed
    await client.put(_url(project_id, f"/{req_id}"), json={"confirm_status": "confirmed"}, headers=h)
    resp = await client.put(_url(project_id, f"/{req_id}"), json={"summary": "修改内容"}, headers=h)
    assert resp.status_code == 422
    assert "已确认的需求版本不可修改内容" in resp.json()["detail"]


async def test_put_confirmed_requirement_version_no_rejected(client, db):
    """test_put_confirmed_requirement_version_no_rejected → FR-501"""
    _, project_id = db
    h = await _login(client)
    r = await client.post(_url(project_id), json={"version_no": "v1.0", "summary": "内容"}, headers=h)
    req_id = r.json()["id"]
    await client.put(_url(project_id, f"/{req_id}"), json={"confirm_status": "confirmed"}, headers=h)
    resp = await client.put(_url(project_id, f"/{req_id}"), json={"version_no": "v2.0"}, headers=h)
    assert resp.status_code == 422


async def test_put_confirmed_requirement_notes_allowed(client, db):
    """test_put_confirmed_requirement_notes_allowed → FR-501"""
    _, project_id = db
    h = await _login(client)
    r = await client.post(_url(project_id), json={"version_no": "v1.0", "summary": "内容"}, headers=h)
    req_id = r.json()["id"]
    await client.put(_url(project_id, f"/{req_id}"), json={"confirm_status": "confirmed"}, headers=h)
    resp = await client.put(_url(project_id, f"/{req_id}"), json={"notes": "新备注"}, headers=h)
    assert resp.status_code == 200
    assert resp.json()["notes"] == "新备注"


async def test_patch_confirmed_requirement_summary_rejected(client, db):
    """test_patch_confirmed_requirement_summary_rejected → FR-501（PATCH 同样约束）"""
    _, project_id = db
    h = await _login(client)
    r = await client.post(_url(project_id), json={"version_no": "v1.0", "summary": "内容"}, headers=h)
    req_id = r.json()["id"]
    await client.put(_url(project_id, f"/{req_id}"), json={"confirm_status": "confirmed"}, headers=h)
    resp = await client.patch(_url(project_id, f"/{req_id}"), json={"summary": "修改"}, headers=h)
    assert resp.status_code == 422
    assert "已确认的需求版本不可修改内容" in resp.json()["detail"]


async def test_patch_confirmed_requirement_notes_allowed(client, db):
    """test_patch_confirmed_requirement_notes_allowed → FR-501"""
    _, project_id = db
    h = await _login(client)
    r = await client.post(_url(project_id), json={"version_no": "v1.0", "summary": "内容"}, headers=h)
    req_id = r.json()["id"]
    await client.put(_url(project_id, f"/{req_id}"), json={"confirm_status": "confirmed"}, headers=h)
    resp = await client.patch(_url(project_id, f"/{req_id}"), json={"notes": "PATCH备注"}, headers=h)
    assert resp.status_code == 200
    assert resp.json()["notes"] == "PATCH备注"


async def test_set_current_clears_other_versions(client, db):
    """test_set_current_clears_other_versions → FR-501"""
    _, project_id = db
    h = await _login(client)
    r1 = await client.post(_url(project_id), json={"version_no": "v1.0", "summary": "第一版"}, headers=h)
    r2 = await client.post(_url(project_id), json={"version_no": "v2.0", "summary": "第二版"}, headers=h)
    id1, id2 = r1.json()["id"], r2.json()["id"]
    # v2 是 current, 设置 v1 为 current
    resp = await client.post(_url(project_id, f"/{id1}/set-current"), headers=h)
    assert resp.status_code == 200
    assert resp.json()["is_current"] is True
    # v2 不再是 current
    detail = await client.get(_url(project_id, f"/{id2}"), headers=h)
    assert detail.json()["is_current"] is False


async def test_set_current_no_two_current_same_project(client, db):
    """test_set_current_no_two_current_same_project → FR-501（唯一性）"""
    _, project_id = db
    h = await _login(client)
    r1 = await client.post(_url(project_id), json={"version_no": "v1.0", "summary": "第一版"}, headers=h)
    r2 = await client.post(_url(project_id), json={"version_no": "v2.0", "summary": "第二版"}, headers=h)
    r3 = await client.post(_url(project_id), json={"version_no": "v3.0", "summary": "第三版"}, headers=h)
    # 设置 v1 为 current
    await client.post(_url(project_id, f"/{r1.json()['id']}/set-current"), headers=h)
    # 验证只有一条 current
    items = (await client.get(_url(project_id), headers=h)).json()
    current_count = sum(1 for i in items if i["is_current"])
    assert current_count == 1


async def test_create_change_billable_without_order_rejected(client, db):
    """test_create_change_billable_without_order_rejected → FR-501"""
    _, project_id = db
    h = await _login(client)
    r = await client.post(_url(project_id), json={"version_no": "v1.0", "summary": "内容"}, headers=h)
    req_id = r.json()["id"]
    resp = await client.post(
        _url(project_id, f"/{req_id}/changes"),
        json={"title": "收费变更", "description": "额外功能", "change_type": "add", "is_billable": True, "initiated_by": "customer"},
        headers=h,
    )
    assert resp.status_code == 422
    assert "收费变更必须先关联或创建变更单" in resp.json()["detail"]


async def test_create_change_not_billable_success(client, db):
    """test_create_change_not_billable_success → FR-501"""
    _, project_id = db
    h = await _login(client)
    r = await client.post(_url(project_id), json={"version_no": "v1.0", "summary": "内容"}, headers=h)
    req_id = r.json()["id"]
    resp = await client.post(
        _url(project_id, f"/{req_id}/changes"),
        json={"title": "免费变更", "description": "小调整", "change_type": "modify", "is_billable": False, "initiated_by": "internal"},
        headers=h,
    )
    assert resp.status_code == 201
    assert resp.json()["is_billable"] is False


async def test_create_change_billable_with_order_success(client, db):
    """test_create_change_billable_with_order_success → FR-501"""
    session, project_id = db
    h = await _login(client)
    r = await client.post(_url(project_id), json={"version_no": "v1.0", "summary": "内容"}, headers=h)
    req_id = r.json()["id"]
    # 创建变更单
    co = ChangeOrder(order_no="BG-20260407-001", contract_id=999, title="测试变更单", description="描述", amount=1000)
    session.add(co)
    await session.commit()
    await session.refresh(co)
    resp = await client.post(
        _url(project_id, f"/{req_id}/changes"),
        json={"title": "收费变更", "description": "额外功能", "change_type": "add", "is_billable": True, "change_order_id": co.id, "initiated_by": "customer"},
        headers=h,
    )
    assert resp.status_code == 201
    assert resp.json()["change_order_id"] == co.id


async def test_project_not_found_returns_404(client, db):
    """test_project_not_found_returns_404 → FR-501"""
    _, _ = db
    h = await _login(client)
    r = await client.get("/api/v1/projects/99999/requirements", headers=h)
    assert r.status_code == 404
