"""FR-503 交付物管理测试——严格对应 prd1_5.md 簇 D 测试用例清单"""
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
from app.core.deliverable_utils import contains_password_field

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


async def _login(client: AsyncClient) -> dict:
    r = await client.post("/api/v1/auth/login", data={"username": "admin", "password": "admin123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _url(project_id: int, suffix: str = "") -> str:
    return f"/api/v1/projects/{project_id}/deliverables{suffix}"


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


def _make_dlv(dtype: str = "source_code") -> dict:
    return {
        "name": "源码包",
        "deliverable_type": dtype,
        "delivery_date": "2026-04-07",
        "recipient_name": "李总",
        "delivery_method": "repository",
    }


# ── 独立函数测试 ──────────────────────────────────────────────


def test_contains_password_field_detects_password():
    assert contains_password_field({"account_password": "x"}) is True


def test_contains_password_field_detects_pwd():
    assert contains_password_field({"user_pwd": "x"}) is True


def test_contains_password_field_detects_token():
    assert contains_password_field({"api_token": "x"}) is True


def test_contains_password_field_allows_normal_fields():
    assert contains_password_field({"account_name": "admin", "notes": "备注"}) is False


def test_contains_password_field_checks_name_not_value():
    """只检测字段名，不扫描字段值"""
    # 值里包含 "密码" 但字段名是 notes → 放行
    assert contains_password_field({"notes": "密码已通过微信发送"}) is False


# ── API 接口测试 ─────────────────────────────────────────────


async def test_create_source_code_deliverable(client, db):
    """test_create_source_code_deliverable → FR-503"""
    _, project_id = db
    h = await _login(client)
    r = await client.post(_url(project_id), json=_make_dlv("source_code"), headers=h)
    assert r.status_code == 201
    assert r.json()["deliverable_type"] == "source_code"


async def test_create_account_handover_with_valid_accounts(client, db):
    """test_create_account_handover_with_valid_accounts → FR-503"""
    _, project_id = db
    h = await _login(client)
    r = await client.post(_url(project_id), json={
        **_make_dlv("account_handover"),
        "account_handovers": [
            {"platform_name": "阿里云", "account_name": "admin@example.com"},
            {"platform_name": "腾讯云", "account_name": "user@test.com", "notes": "主账号"},
        ],
    }, headers=h)
    assert r.status_code == 201


async def test_create_account_handover_password_field_rejected(client, db):
    """test_create_account_handover_password_field_rejected → FR-503"""
    _, project_id = db
    h = await _login(client)
    r = await client.post(_url(project_id), json={
        **_make_dlv("account_handover"),
        "account_handovers": [{"platform_name": "阿里云", "account_name": "admin", "account_password": "123456"}],
    }, headers=h)
    assert r.status_code == 422
    assert "禁止存储密码" in r.json()["detail"]


async def test_create_account_handover_pwd_field_rejected(client, db):
    """test_create_account_handover_pwd_field_rejected → FR-503"""
    _, project_id = db
    h = await _login(client)
    r = await client.post(_url(project_id), json={
        **_make_dlv("account_handover"),
        "account_handovers": [{"platform_name": "阿里云", "account_name": "admin", "user_pwd": "xxx"}],
    }, headers=h)
    assert r.status_code == 422


async def test_create_account_handover_token_field_rejected(client, db):
    """test_create_account_handover_token_field_rejected → FR-503"""
    _, project_id = db
    h = await _login(client)
    r = await client.post(_url(project_id), json={
        **_make_dlv("account_handover"),
        "account_handovers": [{"platform_name": "阿里云", "account_name": "admin", "api_token": "xxx"}],
    }, headers=h)
    assert r.status_code == 422


async def test_create_account_handover_notes_field_allowed(client, db):
    """test_create_account_handover_notes_field_allowed → FR-503（notes 是合法字段名）"""
    _, project_id = db
    h = await _login(client)
    r = await client.post(_url(project_id), json={
        **_make_dlv("account_handover"),
        "account_handovers": [{"platform_name": "阿里云", "account_name": "admin", "notes": "主账号"}],
    }, headers=h)
    assert r.status_code == 201


async def test_account_handovers_saved_in_same_transaction(client, db):
    """test_account_handovers_saved_in_same_transaction → FR-503"""
    session, project_id = db
    h = await _login(client)
    r = await client.post(_url(project_id), json={
        **_make_dlv("account_handover"),
        "account_handovers": [
            {"platform_name": "阿里云", "account_name": "admin"},
            {"platform_name": "腾讯云", "account_name": "user"},
        ],
    }, headers=h)
    assert r.status_code == 201
    dlv_id = r.json()["id"]
    # 验证详情包含 handovers
    detail = await client.get(_url(project_id, f"/{dlv_id}"), headers=h)
    data = detail.json()
    assert len(data["account_handovers"]) == 2


async def test_get_deliverables_ordered_by_date_desc(client, db):
    """test_get_deliverables_ordered_by_date_desc → FR-503"""
    _, project_id = db
    h = await _login(client)
    await client.post(_url(project_id), json={**_make_dlv(), "delivery_date": "2026-01-01"}, headers=h)
    await client.post(_url(project_id), json={**_make_dlv(), "delivery_date": "2026-03-01"}, headers=h)
    await client.post(_url(project_id), json={**_make_dlv(), "delivery_date": "2026-02-01"}, headers=h)
    r = await client.get(_url(project_id), headers=h)
    items = r.json()
    assert items[0]["delivery_date"] == "2026-03-01"
    assert items[2]["delivery_date"] == "2026-01-01"


async def test_get_deliverables_filter_by_type(client, db):
    """test_get_deliverables_filter_by_type → FR-503"""
    _, project_id = db
    h = await _login(client)
    await client.post(_url(project_id), json=_make_dlv("source_code"), headers=h)
    await client.post(_url(project_id), json=_make_dlv("api_doc"), headers=h)
    r = await client.get(_url(project_id), params={"deliverable_type": "api_doc"}, headers=h)
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1
    assert items[0]["deliverable_type"] == "api_doc"


async def test_get_deliverable_detail_includes_handovers(client, db):
    """test_get_deliverable_detail_includes_handovers → FR-503"""
    _, project_id = db
    h = await _login(client)
    r = await client.post(_url(project_id), json={
        **_make_dlv("account_handover"),
        "account_handovers": [{"platform_name": "阿里云", "account_name": "admin"}],
    }, headers=h)
    dlv_id = r.json()["id"]
    detail = await client.get(_url(project_id, f"/{dlv_id}"), headers=h)
    assert "account_handovers" in detail.json()
    assert len(detail.json()["account_handovers"]) == 1


async def test_delete_deliverable_returns_405(client, db):
    """test_delete_deliverable_returns_405 → FR-503"""
    _, project_id = db
    h = await _login(client)
    r = await client.post(_url(project_id), json=_make_dlv(), headers=h)
    dlv_id = r.json()["id"]
    resp = await client.delete(_url(project_id, f"/{dlv_id}"), headers=h)
    assert resp.status_code == 405


async def test_project_not_found_returns_404(client, db):
    """test_project_not_found_returns_404 → FR-503"""
    _, _ = db
    h = await _login(client)
    r = await client.get("/api/v1/projects/99999/deliverables", headers=h)
    assert r.status_code == 404
