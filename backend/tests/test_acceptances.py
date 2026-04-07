"""FR-502 验收管理测试——严格对应 prd1_5.md 簇 C 测试用例清单"""
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
from app.models.reminder import Reminder
from app.core.security import get_password_hash
from app.core.acceptance_utils import append_notes

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


async def _login(client: AsyncClient) -> dict:
    r = await client.post("/api/v1/auth/login", data={"username": "admin", "password": "admin123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _url(project_id: int, suffix: str = "") -> str:
    return f"/api/v1/projects/{project_id}/acceptances{suffix}"


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


def _make_acceptance(result: str = "passed", trigger: bool = True) -> dict:
    return {
        "acceptance_name": "一期验收",
        "acceptance_date": "2026-04-07",
        "acceptor_name": "李总",
        "result": result,
        "confirm_method": "offline",
        "trigger_payment_reminder": trigger,
    }


# ── 独立函数测试 ──────────────────────────────────────────────


def test_append_notes_adds_newline_separator():
    assert append_notes("旧备注", "新备注") == "旧备注\n新备注"


def test_append_notes_empty_original_no_separator():
    assert append_notes(None, "新备注") == "新备注"
    assert append_notes("", "新备注") == "新备注"


# ── API 接口测试 ─────────────────────────────────────────────


async def test_create_acceptance_passed_triggers_reminder(client, db):
    """test_create_acceptance_passed_triggers_reminder → FR-502"""
    session, project_id = db
    h = await _login(client)
    r = await client.post(_url(project_id), json=_make_acceptance("passed", True), headers=h)
    assert r.status_code == 201
    data = r.json()
    assert data["reminder_id"] is not None
    # 验证 Reminder 确实存在
    reminder = await session.get(Reminder, data["reminder_id"])
    assert reminder is not None
    assert "收款提醒" in reminder.title


async def test_create_acceptance_conditional_triggers_reminder(client, db):
    """test_create_acceptance_conditional_triggers_reminder → FR-502"""
    session, project_id = db
    h = await _login(client)
    r = await client.post(_url(project_id), json=_make_acceptance("conditional", True), headers=h)
    assert r.status_code == 201
    assert r.json()["reminder_id"] is not None


async def test_create_acceptance_failed_no_reminder(client, db):
    """test_create_acceptance_failed_no_reminder → FR-502"""
    _, project_id = db
    h = await _login(client)
    r = await client.post(_url(project_id), json=_make_acceptance("failed", True), headers=h)
    assert r.status_code == 201
    assert r.json()["reminder_id"] is None


async def test_create_acceptance_flag_false_no_reminder(client, db):
    """test_create_acceptance_flag_false_no_reminder → FR-502"""
    _, project_id = db
    h = await _login(client)
    r = await client.post(_url(project_id), json=_make_acceptance("passed", False), headers=h)
    assert r.status_code == 201
    assert r.json()["reminder_id"] is None


async def test_reminder_created_in_same_transaction(client, db):
    """test_reminder_created_in_same_transaction → FR-502"""
    session, project_id = db
    h = await _login(client)
    r = await client.post(_url(project_id), json=_make_acceptance("passed", True), headers=h)
    reminder_id = r.json()["reminder_id"]
    # reminder 已写入同一 session
    reminder = await session.get(Reminder, reminder_id)
    assert reminder is not None
    assert reminder.source == "auto"


async def test_reminder_id_written_back_to_acceptance(client, db):
    """test_reminder_id_written_back_to_acceptance → FR-502"""
    _, project_id = db
    h = await _login(client)
    r = await client.post(_url(project_id), json=_make_acceptance("passed", True), headers=h)
    acc_id = r.json()["id"]
    detail = await client.get(_url(project_id, f"/{acc_id}"), headers=h)
    assert detail.json()["reminder_id"] is not None


async def test_get_acceptances_ordered_by_date_desc(client, db):
    """test_get_acceptances_ordered_by_date_desc → FR-502"""
    _, project_id = db
    h = await _login(client)
    await client.post(_url(project_id), json={**_make_acceptance(), "acceptance_date": "2026-01-01"}, headers=h)
    await client.post(_url(project_id), json={**_make_acceptance(), "acceptance_date": "2026-03-01"}, headers=h)
    await client.post(_url(project_id), json={**_make_acceptance(), "acceptance_date": "2026-02-01"}, headers=h)
    r = await client.get(_url(project_id), headers=h)
    items = r.json()
    assert len(items) == 3
    assert items[0]["acceptance_date"] == "2026-03-01"
    assert items[1]["acceptance_date"] == "2026-02-01"
    assert items[2]["acceptance_date"] == "2026-01-01"


async def test_delete_acceptance_returns_405(client, db):
    """test_delete_acceptance_returns_405 → FR-502"""
    _, project_id = db
    h = await _login(client)
    r = await client.post(_url(project_id), json=_make_acceptance(), headers=h)
    acc_id = r.json()["id"]
    resp = await client.delete(_url(project_id, f"/{acc_id}"), headers=h)
    assert resp.status_code == 405


async def test_put_result_field_rejected(client, db):
    """test_put_result_field_rejected → FR-502"""
    _, project_id = db
    h = await _login(client)
    r = await client.post(_url(project_id), json=_make_acceptance(), headers=h)
    acc_id = r.json()["id"]
    resp = await client.put(_url(project_id, f"/{acc_id}"), json={"result": "failed"}, headers=h)
    assert resp.status_code == 422
    assert "验收结果不可修改" in resp.json()["detail"]


async def test_patch_result_field_rejected(client, db):
    """test_patch_result_field_rejected → FR-502（PATCH 同样约束）"""
    _, project_id = db
    h = await _login(client)
    r = await client.post(_url(project_id), json=_make_acceptance(), headers=h)
    acc_id = r.json()["id"]
    resp = await client.patch(_url(project_id, f"/{acc_id}"), json={"result": "failed"}, headers=h)
    assert resp.status_code == 422
    assert "验收结果不可修改" in resp.json()["detail"]


async def test_append_notes_adds_newline_separator_api(client, db):
    """test_append_notes_adds_newline_separator → FR-502"""
    _, project_id = db
    h = await _login(client)
    r = await client.post(_url(project_id), json={**_make_acceptance(), "notes": "初始备注"}, headers=h)
    acc_id = r.json()["id"]
    resp = await client.patch(
        _url(project_id, f"/{acc_id}/append-notes"),
        json={"notes": "追加备注"},
        headers=h,
    )
    assert resp.status_code == 200
    assert resp.json()["notes"] == "初始备注\n追加备注"


async def test_append_notes_empty_original_no_separator_api(client, db):
    """test_append_notes_empty_original_no_separator → FR-502"""
    _, project_id = db
    h = await _login(client)
    r = await client.post(_url(project_id), json={**_make_acceptance(), "notes": None}, headers=h)
    acc_id = r.json()["id"]
    resp = await client.patch(
        _url(project_id, f"/{acc_id}/append-notes"),
        json={"notes": "第一条备注"},
        headers=h,
    )
    assert resp.status_code == 200
    assert resp.json()["notes"] == "第一条备注"


async def test_project_not_found_returns_404(client, db):
    """test_project_not_found_returns_404 → FR-502"""
    _, _ = db
    h = await _login(client)
    r = await client.get("/api/v1/projects/99999/acceptances", headers=h)
    assert r.status_code == 404


async def test_acceptance_detail_response_structure(client, db):
    """test_acceptance_detail_response_structure → FR-502"""
    _, project_id = db
    h = await _login(client)
    r = await client.post(_url(project_id), json=_make_acceptance(), headers=h)
    acc_id = r.json()["id"]
    detail = await client.get(_url(project_id, f"/{acc_id}"), headers=h)
    assert detail.status_code == 200
    data = detail.json()
    # 验证 PRD 要求的所有字段存在
    required_fields = [
        "id", "project_id", "acceptance_name", "acceptance_date",
        "acceptor_name", "result", "notes", "trigger_payment_reminder",
        "reminder_id", "confirm_method", "created_at",
    ]
    for f in required_fields:
        assert f in data, f"缺少字段: {f}"
    # 可空字段必须显式返回 null
    assert data["acceptor_title"] is None or isinstance(data["acceptor_title"], str)
