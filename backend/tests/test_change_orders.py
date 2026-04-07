"""FR-505 变更单/增补单测试——严格对应 prd1_5.md 簇 F 测试用例清单"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from decimal import Decimal
from datetime import date

from app.main import app
from app.database import get_db
from app.models.base import Base
from app.models.user import User
from app.models.customer import Customer
from app.models.project import Project
from app.models.contract import Contract
from app.models.change_order import ChangeOrder
from app.core.security import get_password_hash
from app.core.change_order_utils import validate_status_transition

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


async def _login(client: AsyncClient) -> dict:
    r = await client.post("/api/v1/auth/login", data={"username": "admin", "password": "admin123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _contract_url(contract_id: int, suffix: str = "") -> str:
    return f"/api/v1/contracts/{contract_id}/change-orders{suffix}"


def _project_url(project_id: int) -> str:
    return f"/api/v1/projects/{project_id}/change-orders/summary"


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
        contract = Contract(
            project_id=proj.id, customer_id=cust.id, contract_no="HT-001", title="测试合同",
            amount=100000, signed_date=date(2026, 1, 1),
            start_date=date(2026, 1, 1), end_date=date(2026, 12, 31),
        )
        session.add(contract)
        await session.commit()
        yield session, proj.id, contract.id
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


def _make_order(title: str = "新增功能", amount: str = "5000") -> dict:
    return {"title": title, "description": "新增模块", "amount": amount}


# ── 独立函数测试 ──────────────────────────────────────────────


def test_validate_status_transition_function():
    """test_validate_status_transition_function → FR-505（独立函数测试）"""
    # 合法流转
    assert validate_status_transition("draft", "sent") is True
    assert validate_status_transition("draft", "confirmed") is True
    assert validate_status_transition("draft", "completed") is True
    assert validate_status_transition("sent", "confirmed") is True
    assert validate_status_transition("confirmed", "in_progress") is True
    assert validate_status_transition("in_progress", "completed") is True
    # 非法流转
    assert validate_status_transition("completed", "draft") is False
    assert validate_status_transition("completed", "in_progress") is False
    assert validate_status_transition("draft", "in_progress") is False


# ── API 接口测试 ─────────────────────────────────────────────


async def test_create_change_order_generates_no(client, db):
    """test_create_change_order_generates_no → FR-505"""
    _, _, contract_id = db
    h = await _login(client)
    r = await client.post(_contract_url(contract_id), json=_make_order(), headers=h)
    assert r.status_code == 201
    assert r.json()["order_no"].startswith("BG-")


async def test_change_order_no_format_bg_yyyymmdd_001(client, db):
    """test_change_order_no_format_bg_yyyymmdd_001 → FR-505"""
    _, _, contract_id = db
    h = await _login(client)
    r = await client.post(_contract_url(contract_id), json=_make_order(), headers=h)
    order_no = r.json()["order_no"]
    today_str = date.today().strftime("%Y%m%d")
    assert order_no == f"BG-{today_str}-001"


async def test_change_order_no_increments_same_day(client, db):
    """test_change_order_no_increments_same_day → FR-505"""
    _, _, contract_id = db
    h = await _login(client)
    r1 = await client.post(_contract_url(contract_id), json=_make_order("第一条"), headers=h)
    r2 = await client.post(_contract_url(contract_id), json=_make_order("第二条"), headers=h)
    assert r1.json()["order_no"].endswith("-001")
    assert r2.json()["order_no"].endswith("-002")


async def test_get_change_orders_includes_confirmed_total(client, db):
    """test_get_change_orders_includes_confirmed_total → FR-505"""
    _, _, contract_id = db
    h = await _login(client)
    await client.post(_contract_url(contract_id), json=_make_order(), headers=h)
    r = await client.get(_contract_url(contract_id), headers=h)
    assert "confirmed_total" in r.json()


async def test_get_change_orders_includes_actual_receivable(client, db):
    """test_get_change_orders_includes_actual_receivable → FR-505"""
    _, _, contract_id = db
    h = await _login(client)
    await client.post(_contract_url(contract_id), json=_make_order(), headers=h)
    r = await client.get(_contract_url(contract_id), headers=h)
    assert "actual_receivable" in r.json()


async def test_actual_receivable_includes_confirmed(client, db):
    """test_actual_receivable_includes_confirmed → FR-505"""
    _, _, contract_id = db
    h = await _login(client)
    r = await client.post(_contract_url(contract_id), json=_make_order(amount="5000"), headers=h)
    order_id = r.json()["id"]
    # draft → confirmed
    await client.patch(_contract_url(contract_id, f"/{order_id}"), json={"status": "confirmed"}, headers=h)
    r = await client.get(_contract_url(contract_id), headers=h)
    assert Decimal(r.json()["confirmed_total"]) == Decimal("5000.00")


async def test_actual_receivable_includes_in_progress(client, db):
    """test_actual_receivable_includes_in_progress → FR-505"""
    _, _, contract_id = db
    h = await _login(client)
    r = await client.post(_contract_url(contract_id), json=_make_order(amount="3000"), headers=h)
    order_id = r.json()["id"]
    await client.patch(_contract_url(contract_id, f"/{order_id}"), json={"status": "confirmed"}, headers=h)
    await client.patch(_contract_url(contract_id, f"/{order_id}"), json={"status": "in_progress"}, headers=h)
    r = await client.get(_contract_url(contract_id), headers=h)
    assert Decimal(r.json()["confirmed_total"]) == Decimal("3000.00")


async def test_actual_receivable_includes_completed(client, db):
    """test_actual_receivable_includes_completed → FR-505"""
    _, _, contract_id = db
    h = await _login(client)
    r = await client.post(_contract_url(contract_id), json=_make_order(amount="2000"), headers=h)
    order_id = r.json()["id"]
    await client.patch(_contract_url(contract_id, f"/{order_id}"), json={"status": "completed"}, headers=h)
    r = await client.get(_contract_url(contract_id), headers=h)
    assert Decimal(r.json()["confirmed_total"]) == Decimal("2000.00")


async def test_actual_receivable_excludes_draft(client, db):
    """test_actual_receivable_excludes_draft → FR-505"""
    _, _, contract_id = db
    h = await _login(client)
    await client.post(_contract_url(contract_id), json=_make_order(amount="10000"), headers=h)
    r = await client.get(_contract_url(contract_id), headers=h)
    assert Decimal(r.json()["confirmed_total"]) == Decimal("0.00")


async def test_actual_receivable_excludes_sent(client, db):
    """test_actual_receivable_excludes_sent → FR-505"""
    _, _, contract_id = db
    h = await _login(client)
    r = await client.post(_contract_url(contract_id), json=_make_order(amount="8000"), headers=h)
    order_id = r.json()["id"]
    await client.patch(_contract_url(contract_id, f"/{order_id}"), json={"status": "sent"}, headers=h)
    r = await client.get(_contract_url(contract_id), headers=h)
    assert Decimal(r.json()["confirmed_total"]) == Decimal("0.00")


async def test_status_draft_to_sent_allowed(client, db):
    """test_status_draft_to_sent_allowed → FR-505"""
    _, _, contract_id = db
    h = await _login(client)
    r = await client.post(_contract_url(contract_id), json=_make_order(), headers=h)
    order_id = r.json()["id"]
    resp = await client.patch(_contract_url(contract_id, f"/{order_id}"), json={"status": "sent"}, headers=h)
    assert resp.status_code == 200
    assert resp.json()["status"] == "sent"


async def test_status_draft_to_confirmed_allowed(client, db):
    """test_status_draft_to_confirmed_allowed → FR-505（跳过 sent 合法）"""
    _, _, contract_id = db
    h = await _login(client)
    r = await client.post(_contract_url(contract_id), json=_make_order(), headers=h)
    order_id = r.json()["id"]
    resp = await client.patch(_contract_url(contract_id, f"/{order_id}"), json={"status": "confirmed"}, headers=h)
    assert resp.status_code == 200
    assert resp.json()["status"] == "confirmed"


async def test_status_draft_to_completed_allowed(client, db):
    """test_status_draft_to_completed_allowed → FR-505（提前终止合法）"""
    _, _, contract_id = db
    h = await _login(client)
    r = await client.post(_contract_url(contract_id), json=_make_order(), headers=h)
    order_id = r.json()["id"]
    resp = await client.patch(_contract_url(contract_id, f"/{order_id}"), json={"status": "completed"}, headers=h)
    assert resp.status_code == 200


async def test_status_completed_to_any_rejected(client, db):
    """test_status_completed_to_any_rejected → FR-505"""
    _, _, contract_id = db
    h = await _login(client)
    r = await client.post(_contract_url(contract_id), json=_make_order(), headers=h)
    order_id = r.json()["id"]
    await client.patch(_contract_url(contract_id, f"/{order_id}"), json={"status": "completed"}, headers=h)
    resp = await client.patch(_contract_url(contract_id, f"/{order_id}"), json={"status": "draft"}, headers=h)
    assert resp.status_code == 422


async def test_status_illegal_transition_returns_422_with_message(client, db):
    """test_status_illegal_transition_returns_422_with_message → FR-505"""
    _, _, contract_id = db
    h = await _login(client)
    r = await client.post(_contract_url(contract_id), json=_make_order(), headers=h)
    order_id = r.json()["id"]
    resp = await client.patch(_contract_url(contract_id, f"/{order_id}"), json={"status": "in_progress"}, headers=h)
    assert resp.status_code == 422
    assert "不被允许" in resp.json()["detail"]


async def test_update_draft_amount_success(client, db):
    """test_update_draft_amount_success → FR-505"""
    _, _, contract_id = db
    h = await _login(client)
    r = await client.post(_contract_url(contract_id), json=_make_order(), headers=h)
    order_id = r.json()["id"]
    resp = await client.put(_contract_url(contract_id, f"/{order_id}"), json={"amount": "8000"}, headers=h)
    assert resp.status_code == 200
    assert Decimal(resp.json()["amount"]) == Decimal("8000")


async def test_update_confirmed_amount_rejected(client, db):
    """test_update_confirmed_amount_rejected → FR-505"""
    _, _, contract_id = db
    h = await _login(client)
    r = await client.post(_contract_url(contract_id), json=_make_order(), headers=h)
    order_id = r.json()["id"]
    await client.patch(_contract_url(contract_id, f"/{order_id}"), json={"status": "confirmed"}, headers=h)
    resp = await client.put(_contract_url(contract_id, f"/{order_id}"), json={"amount": "99999"}, headers=h)
    assert resp.status_code == 422
    assert "已确认的变更单不可修改金额和描述" in resp.json()["detail"]


async def test_update_confirmed_description_rejected(client, db):
    """test_update_confirmed_description_rejected → FR-505"""
    _, _, contract_id = db
    h = await _login(client)
    r = await client.post(_contract_url(contract_id), json=_make_order(), headers=h)
    order_id = r.json()["id"]
    await client.patch(_contract_url(contract_id, f"/{order_id}"), json={"status": "confirmed"}, headers=h)
    resp = await client.put(_contract_url(contract_id, f"/{order_id}"), json={"description": "修改描述"}, headers=h)
    assert resp.status_code == 422


async def test_patch_confirmed_amount_rejected(client, db):
    """test_patch_confirmed_amount_rejected → FR-505（PATCH 同样约束）"""
    _, _, contract_id = db
    h = await _login(client)
    r = await client.post(_contract_url(contract_id), json=_make_order(), headers=h)
    order_id = r.json()["id"]
    await client.patch(_contract_url(contract_id, f"/{order_id}"), json={"status": "confirmed"}, headers=h)
    resp = await client.patch(_contract_url(contract_id, f"/{order_id}"), json={"amount": "99999"}, headers=h)
    assert resp.status_code == 422


async def test_project_summary_endpoint_readonly(client, db):
    """test_project_summary_endpoint_readonly → FR-505（无写操作入口）"""
    session, project_id, contract_id = db
    h = await _login(client)
    # 创建变更单
    await client.post(_contract_url(contract_id), json=_make_order(), headers=h)
    # 项目摘要端点只返回列表
    r = await client.get(_project_url(project_id), headers=h)
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1
    assert items[0]["contract_no"] == "HT-001"
    # 确认只有 summary 端点，无 POST/PUT/PATCH 入口
    # POST 应该返回 405（方法不允许）
    post_r = await client.post(_project_url(project_id), json={}, headers=h)
    assert post_r.status_code == 405


async def test_generate_change_order_no_unique(client, db):
    """test_generate_change_order_no_unique → FR-505（独立函数测试）"""
    _, _, contract_id = db
    h = await _login(client)
    r1 = await client.post(_contract_url(contract_id), json=_make_order("A"), headers=h)
    r2 = await client.post(_contract_url(contract_id), json=_make_order("B"), headers=h)
    assert r1.json()["order_no"] != r2.json()["order_no"]
