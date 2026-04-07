"""v1.5 迁移验证测试——确认 8 张新表存在、关键列存在、模型可 CRUD、UNIQUE 约束。"""
import pytest
import pytest_asyncio
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from datetime import date

from app.models.project import Project
from app.models.customer import Customer
from app.models.requirement import Requirement, RequirementChange
from app.models.acceptance import Acceptance
from app.models.deliverable import Deliverable, AccountHandover
from app.models.release import Release
from app.models.change_order import ChangeOrder
from app.models.maintenance import MaintenancePeriod
from app.models.contract import Contract


async def _ensure_customer(db_session: AsyncSession) -> Customer:
    result = await db_session.execute(select(Customer).where(Customer.is_deleted == False).limit(1))
    c = result.scalar_one_or_none()
    if c:
        return c
    c = Customer(name="测试客户", contact_person="张三", phone="13800000000", company="测试公司", source="referral")
    db_session.add(c)
    await db_session.commit()
    await db_session.refresh(c)
    return c
async def _ensure_project(db_session: AsyncSession) -> Project:
    result = await db_session.execute(select(Project).where(Project.is_deleted == False).limit(1))
    p = result.scalar_one_or_none()
    if p:
        return p
    customer = await _ensure_customer(db_session)
    p = Project(name="测试项目", customer_id=customer.id, description="测试")
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)
    return p
async def _ensure_contract(db_session: AsyncSession) -> Contract:
    result = await db_session.execute(select(Contract).where(Contract.is_deleted == False).limit(1))
    c = result.scalar_one_or_none()
    if c:
        return c
    customer = await _ensure_customer(db_session)
    project = await _ensure_project(db_session)
    c = Contract(
        contract_no=f"HT-{date.today().strftime('%Y%m%d')}-001",
        project_id=project.id, customer_id=customer.id,
        title="测试合同", amount=100000.00, signed_date=date.today(), status="active",
    )
    db_session.add(c)
    await db_session.commit()
    await db_session.refresh(c)
    return c
@pytest.mark.asyncio
async def test_all_8_new_tables_exist(db_session: AsyncSession):
    expected = {
        "requirements", "requirement_changes", "change_orders",
        "acceptances", "deliverables", "account_handovers",
        "releases", "maintenance_periods",
    }
    result = await db_session.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
    existing = {row[0] for row in result.fetchall()}
    missing = expected - existing
    assert not missing, f"缺少表: {missing}"


@pytest.mark.asyncio
async def test_requirements_table_columns(db_session: AsyncSession):
    result = await db_session.execute(text("PRAGMA table_info('requirements')"))
    cols = {row[1] for row in result.fetchall()}
    for col in ["project_id", "version_no", "summary", "confirm_status", "confirmed_at", "confirm_method", "is_current", "notes"]:
        assert col in cols, f"requirements 缺少列: {col}"


@pytest.mark.asyncio
async def test_change_orders_table_columns(db_session: AsyncSession):
    result = await db_session.execute(text("PRAGMA table_info('change_orders')"))
    cols = {row[1] for row in result.fetchall()}
    for col in ["contract_id", "order_no", "title", "description", "amount", "status", "confirmed_at", "confirm_method", "notes"]:
        assert col in cols, f"change_orders 缺少列: {col}"


@pytest.mark.asyncio
async def test_acceptances_table_columns(db_session: AsyncSession):
    result = await db_session.execute(text("PRAGMA table_info('acceptances')"))
    cols = {row[1] for row in result.fetchall()}
    for col in ["project_id", "milestone_id", "acceptance_name", "acceptance_date", "acceptor_name", "acceptor_title", "result", "notes", "trigger_payment_reminder", "reminder_id", "confirm_method"]:
        assert col in cols, f"acceptances 缺少列: {col}"


@pytest.mark.asyncio
async def test_deliverables_table_columns(db_session: AsyncSession):
    result = await db_session.execute(text("PRAGMA table_info('deliverables')"))
    cols = {row[1] for row in result.fetchall()}
    for col in ["project_id", "acceptance_id", "name", "deliverable_type", "delivery_date", "recipient_name", "delivery_method", "description", "storage_location", "version_no"]:
        assert col in cols, f"deliverables 缺少列: {col}"


@pytest.mark.asyncio
async def test_releases_table_columns(db_session: AsyncSession):
    result = await db_session.execute(text("PRAGMA table_info('releases')"))
    cols = {row[1] for row in result.fetchall()}
    for col in ["project_id", "deliverable_id", "version_no", "release_date", "release_type", "is_current_online", "changelog", "deploy_env", "notes"]:
        assert col in cols, f"releases 缺少列: {col}"


@pytest.mark.asyncio
async def test_maintenance_periods_table_columns(db_session: AsyncSession):
    result = await db_session.execute(text("PRAGMA table_info('maintenance_periods')"))
    cols = {row[1] for row in result.fetchall()}
    for col in ["project_id", "contract_id", "service_type", "service_description", "start_date", "end_date", "annual_fee", "status", "renewed_by_id", "notes"]:
        assert col in cols, f"maintenance_periods 缺少列: {col}"


@pytest.mark.asyncio
async def test_requirement_changes_table_columns(db_session: AsyncSession):
    result = await db_session.execute(text("PRAGMA table_info('requirement_changes')"))
    cols = {row[1] for row in result.fetchall()}
    for col in ["requirement_id", "title", "description", "change_type", "is_billable", "change_order_id", "initiated_by"]:
        assert col in cols, f"requirement_changes 缺少列: {col}"


@pytest.mark.asyncio
async def test_change_order_no_unique_constraint(db_session: AsyncSession):
    """NFR-501: change_orders.order order_noUN编号被拦截"""
    contract = await _ensure_contract(db_session)
    co1 = ChangeOrder(order_no="BG-20260407-001", contract_id=contract.id, title="变更单1", description="描述", amount=10000.00)
    db_session.add(co1)
    await db_session.commit()

    co2 = ChangeOrder(order_no="BG-20260407-001", contract_id=contract.id, title="变更单2", description="描述", amount=5000.00)
    db_session.add(co2)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_requirement_crud(db_session: AsyncSession):
    project = await _ensure_project(db_session)
    req = Requirement(project_id=project.id, version_no="v1.0", summary="测试需求", is_current=True")
    db_session.add(req)
    await db_session.commit()
    await db_session.refresh(req)
    assert req.id is not None
    assert req.is_current is True


@pytest.mark.asyncio
async def test_requirement_change_crud(db_session: AsyncSession):
    project = await _ensure_project(db_session)
    req = Requirement(project_id=project.id, version_no="v1.0", summary="测试需求", is_current")
    db_session.add(change)
    await db_session.commit()
    await db_session.refresh(change)
    assert change.id is not None


@pytest.mark.asyncio
async def test_acceptance_crud(db_session: AsyncSession):
    project = await _ensure_project(db_session)
    acc = Acceptance(project_id=project.id, acceptance_name="初验", acceptance_date=date.today(), acceptor_name="张三", result="passed", confirm_method="offline")
    db_session.add(acc)
    await db_session.commit()
    await db_session.refresh(acc)
    assert acc.id is not None
    assert acc.result == "passed"


@pytest.mark.asyncio
async def test_deliverable_and_handover_crud(db_session: AsyncSession):
    project = await _ensure_project(db_session)
    d = Deliverable(project_id=project.id, name="测试交付", deliverable_type="account_handover", delivery_date=date.today(), recipient_name="李四", delivery_method="remote")
    db_session.add(d)
    await db_session.commit()
    await db_session.refresh(d)
    h = AccountHandover(deliverable_id=d.id, platform_name="微信公众号", account_name="test_acc")
    db_session.add(h)
    await db_session.commit()
    await db_session.refresh(h)
    assert h.id is not None
    assert h.deliverable_id == d.id