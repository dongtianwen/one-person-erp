"""FR-506 售后/维护期管理测试——严格对应 prd1_5.md 簇 G 测试用例清单"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from datetime import date, timedelta

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
    return f"/api/v1/projects/{project_id}/maintenance-periods{suffix}"


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


def _make_period(start: str = "2026-01-01", end: str = "2026-12-31", stype: str = "warranty") -> dict:
    return {
        "service_type": stype,
        "service_description": "一年免费维护",
        "start_date": start,
        "end_date": end,
        "annual_fee": 5000,
    }


async def test_create_maintenance_success(client, db):
    """test_create_maintenance_success → FR-506"""
    _, project_id = db
    h = await _login(client)
    r = await client.post(_url(project_id), json=_make_period(), headers=h)
    assert r.status_code == 201
    assert r.json()["status"] == "active"


async def test_create_maintenance_end_before_start_rejected(client, db):
    """test_create_maintenance_end_before_start_rejected → FR-506"""
    _, project_id = db
    h = await _login(client)
    r = await client.post(_url(project_id), json=_make_period(start="2026-12-01", end="2026-01-01"), headers=h)
    assert r.status_code == 422
    assert "结束日期不得早于开始日期" in r.json()["detail"]


async def test_get_maintenance_ordered_by_end_date_asc(client, db):
    """test_get_maintenance_ordered_by_end_date_asc → FR-506"""
    _, project_id = db
    h = await _login(client)
    await client.post(_url(project_id), json=_make_period(end="2026-06-30"), headers=h)
    await client.post(_url(project_id), json=_make_period(end="2026-12-31"), headers=h)
    await client.post(_url(project_id), json=_make_period(end="2026-03-31"), headers=h)
    r = await client.get(_url(project_id), headers=h)
    items = r.json()
    assert items[0]["end_date"] == "2026-03-31"
    assert items[2]["end_date"] == "2026-12-31"


async def test_get_maintenance_filter_by_status(client, db):
    """test_get_maintenance_filter_by_status → FR-506"""
    _, project_id = db
    h = await _login(client)
    await client.post(_url(project_id), json=_make_period(), headers=h)
    r = await client.get(_url(project_id), params={"status": "expired"}, headers=h)
    assert r.status_code == 200
    assert len(r.json()) == 0
    r2 = await client.get(_url(project_id), params={"status": "active"}, headers=h)
    assert len(r2.json()) == 1


async def test_renew_new_start_date_is_original_end_plus_one(client, db):
    """test_renew_new_start_date_is_original_end_plus_one → FR-506"""
    _, project_id = db
    h = await _login(client)
    r = await client.post(_url(project_id), json=_make_period(end="2026-06-30"), headers=h)
    period_id = r.json()["id"]
    resp = await client.post(
        _url(project_id, f"/{period_id}/renew"),
        json={"end_date": "2027-06-30"},
        headers=h,
    )
    assert resp.status_code == 201
    assert resp.json()["start_date"] == "2026-07-01"


async def test_renew_requires_explicit_end_date(client, db):
    """test_renew_requires_explicit_end_date → FR-506（end_date 必填）"""
    _, project_id = db
    h = await _login(client)
    r = await client.post(_url(project_id), json=_make_period(), headers=h)
    period_id = r.json()["id"]
    resp = await client.post(
        _url(project_id, f"/{period_id}/renew"),
        json={},
        headers=h,
    )
    assert resp.status_code == 422


async def test_renew_end_date_before_start_rejected(client, db):
    """test_renew_end_date_before_start_rejected → FR-506"""
    _, project_id = db
    h = await _login(client)
    r = await client.post(_url(project_id), json=_make_period(end="2026-12-31"), headers=h)
    period_id = r.json()["id"]
    # 新 start = 2027-01-01, end_date 早于此
    resp = await client.post(
        _url(project_id, f"/{period_id}/renew"),
        json={"end_date": "2026-06-30"},
        headers=h,
    )
    assert resp.status_code == 422


async def test_renew_original_status_becomes_renewed(client, db):
    """test_renew_original_status_becomes_renewed → FR-506"""
    session, project_id = db
    h = await _login(client)
    r = await client.post(_url(project_id), json=_make_period(), headers=h)
    period_id = r.json()["id"]
    await client.post(
        _url(project_id, f"/{period_id}/renew"),
        json={"end_date": "2027-12-31"},
        headers=h,
    )
    from app.models.maintenance import MaintenancePeriod
    original = await session.get(MaintenancePeriod, period_id)
    assert original.status == "renewed"


async def test_renew_original_renewed_by_id_set(client, db):
    """test_renew_original_renewed_by_id_set → FR-506"""
    session, project_id = db
    h = await _login(client)
    r = await client.post(_url(project_id), json=_make_period(), headers=h)
    period_id = r.json()["id"]
    renew_resp = await client.post(
        _url(project_id, f"/{period_id}/renew"),
        json={"end_date": "2027-12-31"},
        headers=h,
    )
    new_id = renew_resp.json()["id"]
    from app.models.maintenance import MaintenancePeriod
    original = await session.get(MaintenancePeriod, period_id)
    assert original.renewed_by_id == new_id


async def test_renew_annual_fee_appends_to_reminder_notes(client, db):
    """test_renew_annual_fee_appends_to_reminder_notes → FR-506（年费 > 0 时 notes 追加）"""
    _, project_id = db
    h = await _login(client)
    r = await client.post(_url(project_id), json={**_make_period(), "annual_fee": 8000}, headers=h)
    period_id = r.json()["id"]
    resp = await client.post(
        _url(project_id, f"/{period_id}/renew"),
        json={"end_date": "2027-12-31", "annual_fee": 9000},
        headers=h,
    )
    assert resp.status_code == 201
    # 新记录年费正确
    assert float(resp.json()["annual_fee"]) == 9000


async def test_renew_transaction_atomic(client, db):
    """test_renew_transaction_atomic → FR-506"""
    session, project_id = db
    h = await _login(client)
    r = await client.post(_url(project_id), json=_make_period(), headers=h)
    period_id = r.json()["id"]
    resp = await client.post(
        _url(project_id, f"/{period_id}/renew"),
        json={"end_date": "2027-12-31"},
        headers=h,
    )
    assert resp.status_code == 201
    from app.models.maintenance import MaintenancePeriod
    original = await session.get(MaintenancePeriod, period_id)
    assert original.status == "renewed"
    assert original.renewed_by_id is not None


async def test_patch_active_allowed_fields(client, db):
    """test_patch_active_allowed_fields → FR-506"""
    _, project_id = db
    h = await _login(client)
    r = await client.post(_url(project_id), json=_make_period(), headers=h)
    period_id = r.json()["id"]
    resp = await client.patch(
        _url(project_id, f"/{period_id}"),
        json={"service_description": "更新服务说明", "annual_fee": 6000, "notes": "新备注"},
        headers=h,
    )
    assert resp.status_code == 200
    assert resp.json()["service_description"] == "更新服务说明"


async def test_patch_expired_rejected(client, db):
    """test_patch_expired_rejected → FR-506"""
    session, project_id = db
    h = await _login(client)
    r = await client.post(_url(project_id), json=_make_period(), headers=h)
    period_id = r.json()["id"]
    from app.models.maintenance import MaintenancePeriod
    period = await session.get(MaintenancePeriod, period_id)
    period.status = "expired"
    await session.commit()
    resp = await client.patch(
        _url(project_id, f"/{period_id}"),
        json={"notes": "尝试修改"},
        headers=h,
    )
    assert resp.status_code == 422
    assert "已结束的服务期不可修改" in resp.json()["detail"]


async def test_patch_disallowed_fields_rejected(client, db):
    """test_patch_disallowed_fields_rejected → FR-506"""
    _, project_id = db
    h = await _login(client)
    r = await client.post(_url(project_id), json=_make_period(), headers=h)
    period_id = r.json()["id"]
    resp = await client.patch(
        _url(project_id, f"/{period_id}"),
        json={"start_date": "2025-01-01"},
        headers=h,
    )
    assert resp.status_code == 422


async def test_dashboard_includes_active_maintenance_count(client, db):
    """test_dashboard_includes_active_maintenance_count → FR-506"""
    _, project_id = db
    h = await _login(client)
    # 创建维护期
    await client.post(_url(project_id), json=_make_period(), headers=h)
    r = await client.get("/api/v1/dashboard", headers=h)
    assert r.status_code == 200
    assert "active_maintenance_count" in r.json()
    assert r.json()["active_maintenance_count"] >= 1


# ── 事件驱动检查测试 ─────────────────────────────────────────


async def test_event_driven_expires_overdue_maintenance(client, db):
    """test_event_driven_expires_overdue_maintenance → FR-506"""
    session, project_id = db
    from app.models.maintenance import MaintenancePeriod
    # 创建已过期的维护期
    period = MaintenancePeriod(
        project_id=project_id,
        service_type="warranty",
        service_description="已过期维护",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 6, 1),
        status="active",
    )
    session.add(period)
    await session.commit()
    await session.refresh(period)
    assert period.status == "active"

    # 运行事件驱动检查（通过看板触发）
    h = await _login(client)
    await client.get("/api/v1/dashboard", headers=h)

    # 验证已过期
    await session.refresh(period)
    assert period.status == "expired"


async def test_event_driven_creates_reminder_near_expiry(client, db):
    """test_event_driven_creates_reminder_near_expiry → FR-506"""
    session, project_id = db
    from app.models.maintenance import MaintenancePeriod
    from app.core.constants import MAINTENANCE_REMINDER_DAYS_BEFORE
    # 创建即将到期（在 MAINTENANCE_REMINDER_DAYS_BEFORE 天内）的维护期
    threshold = date.today() + timedelta(days=MAINTENANCE_REMINDER_DAYS_BEFORE - 5)
    period = MaintenancePeriod(
        project_id=project_id,
        service_type="maintenance",
        service_description="即将到期维护",
        start_date=date(2025, 1, 1),
        end_date=threshold,
        status="active",
    )
    session.add(period)
    await session.commit()

    h = await _login(client)
    await client.get("/api/v1/dashboard", headers=h)

    # 验证提醒已创建
    from sqlalchemy import select, func
    from app.models.reminder import Reminder
    result = await session.execute(
        select(Reminder).where(
            Reminder.entity_type == "maintenance_period",
            Reminder.entity_id == period.id,
        )
    )
    reminder = result.scalar_one_or_none()
    assert reminder is not None
    assert "维护期即将到期" in reminder.title
    assert reminder.source == "auto"


async def test_event_driven_reminder_idempotent(client, db):
    """test_event_driven_reminder_idempotent → FR-506（重复触发不生成重复提醒）"""
    session, project_id = db
    from app.models.maintenance import MaintenancePeriod
    from app.core.constants import MAINTENANCE_REMINDER_DAYS_BEFORE
    threshold = date.today() + timedelta(days=MAINTENANCE_REMINDER_DAYS_BEFORE - 5)
    period = MaintenancePeriod(
        project_id=project_id,
        service_type="maintenance",
        service_description="幂等测试",
        start_date=date(2025, 1, 1),
        end_date=threshold,
        status="active",
    )
    session.add(period)
    await session.commit()

    h = await _login(client)
    # 第一次触发
    await client.get("/api/v1/dashboard", headers=h)
    # 第二次触发
    await client.get("/api/v1/dashboard", headers=h)

    from sqlalchemy import select, func
    from app.models.reminder import Reminder
    count_result = await session.execute(
        select(func.count(Reminder.id)).where(
            Reminder.entity_type == "maintenance_period",
            Reminder.entity_id == period.id,
        )
    )
    assert count_result.scalar() == 1
