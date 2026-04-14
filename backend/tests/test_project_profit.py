"""FR-401 项目利润核算测试。"""
import pytest
from datetime import date, datetime
from decimal import Decimal
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.project import Project
from app.models.contract import Contract
from app.models.finance import FinanceRecord
from app.models.quotation import Quotation
from app.models.project import WorkHourLog
from app.models.fixed_cost import FixedCost
from app.models.input_invoice import InputInvoice
from app.core.profit_utils import (
    calculate_project_income,
    calculate_project_cost,
    calculate_project_profit,
    get_project_labor_cost,
    calculate_project_profit_v19,
    refresh_project_profit_cache,
    get_profit_overview,
)
from app.core.constants import HOURS_PER_DAY


async def _create_test_data(db: AsyncSession) -> dict:
    """创建测试基础数据。"""
    customer = Customer(name="利润测试客户", contact_person="张三", phone="13800000001")
    db.add(customer)
    await db.commit()
    await db.refresh(customer)

    project = Project(name="利润测试项目", customer_id=customer.id, status="executing")
    db.add(project)
    await db.commit()
    await db.refresh(project)

    contract = Contract(
        contract_no="HT-PROFIT-001", customer_id=customer.id,
        title="利润测试合同", amount=100000, status="active",
        project_id=project.id,
    )
    db.add(contract)
    await db.commit()
    await db.refresh(contract)

    return {"customer": customer, "project": project, "contract": contract}


async def _auth(client: AsyncClient) -> dict:
    """获取认证 headers。"""
    r = await client.post("/api/v1/auth/login", data={"username": "admin", "password": "admin123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ── 核心函数测试（直接调用，无需 HTTP）──


@pytest.mark.asyncio
async def test_project_income_from_confirmed_contract_income(db_session: AsyncSession):
    """FR-401: 项目收入来自已确认的关联合同收入"""
    data = await _create_test_data(db_session)
    record = FinanceRecord(
        type="income", amount=50000, date=date(2026, 4, 1),
        status="confirmed", contract_id=data["contract"].id,
    )
    db_session.add(record)
    await db_session.commit()

    income = await calculate_project_income(data["project"].id, db_session)
    assert income == Decimal("50000")


@pytest.mark.asyncio
async def test_project_income_excludes_pending_records(db_session: AsyncSession):
    """FR-401: 待确认收入不计入"""
    data = await _create_test_data(db_session)
    record = FinanceRecord(
        type="income", amount=30000, date=date(2026, 4, 1),
        status="pending", contract_id=data["contract"].id,
    )
    db_session.add(record)
    await db_session.commit()

    income = await calculate_project_income(data["project"].id, db_session)
    assert income == Decimal("0")


@pytest.mark.asyncio
async def test_project_income_excludes_unrelated_contracts(db_session: AsyncSession):
    """FR-401: 不相关合同的收入不计入"""
    data = await _create_test_data(db_session)
    other_customer = Customer(name="其他客户", contact_person="李四", phone="13900000001")
    db_session.add(other_customer)
    await db_session.commit()
    await db_session.refresh(other_customer)

    other_contract = Contract(
        contract_no="HT-OTHER-001", customer_id=other_customer.id,
        title="其他合同", amount=20000, status="active",
    )
    db_session.add(other_contract)
    await db_session.commit()

    record = FinanceRecord(
        type="income", amount=20000, date=date(2026, 4, 1),
        status="confirmed", contract_id=other_contract.id,
    )
    db_session.add(record)
    await db_session.commit()

    income = await calculate_project_income(data["project"].id, db_session)
    assert income == Decimal("0")


@pytest.mark.asyncio
async def test_project_cost_from_related_project_id(db_session: AsyncSession):
    """FR-401: 项目成本来自 related_project_id 关联的已确认支出"""
    data = await _create_test_data(db_session)
    record = FinanceRecord(
        type="expense", amount=8000, date=date(2026, 4, 1),
        status="confirmed", related_project_id=data["project"].id,
    )
    db_session.add(record)
    await db_session.commit()

    cost = await calculate_project_cost(data["project"].id, db_session)
    assert cost == Decimal("8000")


@pytest.mark.asyncio
async def test_project_cost_excludes_unrelated_expenses(db_session: AsyncSession):
    """FR-401: 不相关支出不计入"""
    data = await _create_test_data(db_session)
    record = FinanceRecord(
        type="expense", amount=5000, date=date(2026, 4, 1),
        status="confirmed",
    )
    db_session.add(record)
    await db_session.commit()

    cost = await calculate_project_cost(data["project"].id, db_session)
    assert cost == Decimal("0")


@pytest.mark.asyncio
async def test_project_profit_calculation(db_session: AsyncSession):
    """FR-401: 利润 = 收入 - 成本"""
    data = await _create_test_data(db_session)
    db_session.add_all([
        FinanceRecord(type="income", amount=50000, date=date(2026, 4, 1), status="confirmed", contract_id=data["contract"].id),
        FinanceRecord(type="expense", amount=8000, date=date(2026, 4, 2), status="confirmed", related_project_id=data["project"].id),
    ])
    await db_session.commit()

    result = await calculate_project_profit(data["project"].id, db_session)
    assert result["income"] == Decimal("50000")
    assert result["cost"] == Decimal("8000")
    assert result["profit"] == Decimal("42000")


@pytest.mark.asyncio
async def test_project_profit_margin_correct(db_session: AsyncSession):
    """FR-401: 利润率计算正确"""
    data = await _create_test_data(db_session)
    db_session.add_all([
        FinanceRecord(type="income", amount=50000, date=date(2026, 4, 1), status="confirmed", contract_id=data["contract"].id),
        FinanceRecord(type="expense", amount=8000, date=date(2026, 4, 2), status="confirmed", related_project_id=data["project"].id),
    ])
    await db_session.commit()

    result = await calculate_project_profit(data["project"].id, db_session)
    assert result["profit_margin"] == Decimal("84.00")


@pytest.mark.asyncio
async def test_project_profit_margin_null_when_income_zero(db_session: AsyncSession):
    """FR-401: 收入为 0 时利润率返回 null"""
    data = await _create_test_data(db_session)
    result = await calculate_project_profit(data["project"].id, db_session)
    assert result["profit_margin"] is None


@pytest.mark.asyncio
async def test_project_profit_all_zero_when_no_records(db_session: AsyncSession):
    """FR-401: 无记录时收入、成本、利润均为 0"""
    data = await _create_test_data(db_session)
    result = await calculate_project_profit(data["project"].id, db_session)
    assert result["income"] == Decimal("0")
    assert result["cost"] == Decimal("0")
    assert result["profit"] == Decimal("0")
    assert result["profit_margin"] is None


# ── API 接口测试 ──


@pytest.mark.asyncio
async def test_project_profit_api_structure_exact_match(client: AsyncClient):
    """FR-401: 利润接口返回结构符合 v1.9 规范"""
    h = await _auth(client)

    resp = await client.post("/api/v1/customers", json={
        "name": "API测试客户", "contact_person": "张三", "phone": "13700000001",
    }, headers=h)
    assert resp.status_code == 201
    customer_id = resp.json()["id"]

    resp = await client.post("/api/v1/projects", json={
        "name": "API利润测试项目", "customer_id": customer_id,
    }, headers=h)
    assert resp.status_code == 201
    project_id = resp.json()["id"]

    resp = await client.get(f"/api/v1/projects/{project_id}/profit", headers=h)
    assert resp.status_code == 200
    body = resp.json()
    assert "project_id" in body
    assert "project_name" in body
    assert "revenue" in body
    assert "cost" in body
    assert "profit" in body
    assert "warnings" in body
    assert "received_amount" in body["revenue"]
    assert "labor_cost" in body["cost"]
    assert "gross_profit" in body["profit"]


@pytest.mark.asyncio
async def test_project_not_found_returns_404(client: AsyncClient):
    """FR-401: 不存在的项目返回 404"""
    h = await _auth(client)
    resp = await client.get("/api/v1/projects/99999/profit", headers=h)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_related_project_id_valid_project_accepted(client: AsyncClient):
    """FR-401: 有效的 related_project_id 被接受"""
    h = await _auth(client)

    resp = await client.post("/api/v1/customers", json={
        "name": "关联项目测试客户", "contact_person": "王五", "phone": "13600000001",
    }, headers=h)
    customer_id = resp.json()["id"]

    resp = await client.post("/api/v1/projects", json={
        "name": "关联测试项目", "customer_id": customer_id,
    }, headers=h)
    project_id = resp.json()["id"]

    resp = await client.post("/api/v1/finances", json={
        "type": "expense", "amount": 5000, "date": "2026-04-01",
        "funding_source": "company_account",
        "related_project_id": project_id,
    }, headers=h)
    assert resp.status_code == 201
    assert resp.json()["related_project_id"] == project_id


@pytest.mark.asyncio
async def test_related_project_id_invalid_project_returns_422(client: AsyncClient):
    """FR-401: 不存在的项目 ID 返回 422"""
    h = await _auth(client)
    resp = await client.post("/api/v1/finances", json={
        "type": "expense", "amount": 5000, "date": "2026-04-01",
        "funding_source": "company_account",
        "related_project_id": 99999,
    }, headers=h)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_related_project_id_null_clears_association(client: AsyncClient):
    """FR-401: 传 null 清除项目关联"""
    h = await _auth(client)

    resp = await client.post("/api/v1/customers", json={
        "name": "清空关联客户", "contact_person": "赵六", "phone": "13500000001",
    }, headers=h)
    customer_id = resp.json()["id"]

    resp = await client.post("/api/v1/projects", json={
        "name": "清空关联项目", "customer_id": customer_id,
    }, headers=h)
    project_id = resp.json()["id"]

    resp = await client.post("/api/v1/finances", json={
        "type": "expense", "amount": 3000, "date": "2026-04-01",
        "funding_source": "company_account",
        "related_project_id": project_id,
    }, headers=h)
    assert resp.status_code == 201
    record_id = resp.json()["id"]

    resp = await client.put(f"/api/v1/finances/{record_id}", json={
        "related_project_id": None,
    }, headers=h)
    assert resp.status_code == 200
    assert resp.json()["related_project_id"] is None


@pytest.mark.asyncio
async def test_project_list_includes_profit_fields(client: AsyncClient):
    """FR-401: 项目列表包含利润字段"""
    h = await _auth(client)
    resp = await client.get("/api/v1/projects", headers=h)
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    if len(body) > 0:
        assert "profit" in body[0]
        assert "profit_margin" in body[0]


# ── v1.9 粗利润函数测试 ──


@pytest.mark.asyncio
async def test_v19_labor_cost_with_hours_and_daily_rate(db_session: AsyncSession):
    """v1.9: 有工时和日费率时正确计算 labor_cost"""
    data = await _create_test_data(db_session)
    db_session.add(Quotation(
        quote_no="BJ-V19-001", customer_id=data["customer"].id,
        project_id=data["project"].id, title="测试报价",
        requirement_summary="测试", estimate_days=10, estimate_hours=80,
        daily_rate=Decimal("1500"), direct_cost=0, risk_buffer_rate=0,
        discount_amount=0, tax_rate=0, subtotal_amount=0, tax_amount=0,
        total_amount=15000, valid_until=date(2026, 12, 31),
    ))
    db_session.add_all([
        WorkHourLog(project_id=data["project"].id, hours_spent=Decimal("40"),
                    log_date=datetime(2026, 4, 1), task_description="开发", created_at=datetime.utcnow(), updated_at=datetime.utcnow()),
        WorkHourLog(project_id=data["project"].id, hours_spent=Decimal("40"),
                    log_date=datetime(2026, 4, 2), task_description="测试", created_at=datetime.utcnow(), updated_at=datetime.utcnow()),
    ])
    await db_session.commit()

    result = await get_project_labor_cost(db_session, data["project"].id)
    assert result["hours_total"] == Decimal("80")
    assert result["daily_rate"] == Decimal("1500")
    # labor_cost = (80 / 8) * 1500 = 15000
    assert result["labor_cost"] == Decimal("15000")
    assert result["has_complete_data"] is True


@pytest.mark.asyncio
async def test_v19_labor_cost_without_daily_rate(db_session: AsyncSession):
    """v1.9: 无日费率时 labor_cost 为 None，标记不完整"""
    data = await _create_test_data(db_session)
    db_session.add(WorkHourLog(
        project_id=data["project"].id, hours_spent=Decimal("16"),
        log_date=datetime(2026, 4, 1), task_description="开发",
        created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
    ))
    await db_session.commit()

    result = await get_project_labor_cost(db_session, data["project"].id)
    assert result["labor_cost"] is None
    assert result["has_complete_data"] is False


@pytest.mark.asyncio
async def test_v19_labor_cost_without_hours(db_session: AsyncSession):
    """v1.9: 无工时记录时 labor_cost 为 None"""
    data = await _create_test_data(db_session)
    db_session.add(Quotation(
        quote_no="BJ-V19-002", customer_id=data["customer"].id,
        project_id=data["project"].id, title="测试报价",
        requirement_summary="测试", estimate_days=5,
        daily_rate=Decimal("1000"), direct_cost=0, risk_buffer_rate=0,
        discount_amount=0, tax_rate=0, subtotal_amount=0, tax_amount=0,
        total_amount=5000, valid_until=date(2026, 12, 31),
    ))
    await db_session.commit()

    result = await get_project_labor_cost(db_session, data["project"].id)
    assert result["hours_total"] == Decimal("0")
    assert result["labor_cost"] is None
    assert result["has_complete_data"] is False


@pytest.mark.asyncio
async def test_v19_hours_per_day_constant_used(db_session: AsyncSession):
    """v1.9: HOURS_PER_DAY 常量正确用于计算"""
    data = await _create_test_data(db_session)
    db_session.add(Quotation(
        quote_no="BJ-V19-003", customer_id=data["customer"].id,
        project_id=data["project"].id, title="测试报价",
        requirement_summary="测试", estimate_days=1, estimate_hours=8,
        daily_rate=Decimal("800"), direct_cost=0, risk_buffer_rate=0,
        discount_amount=0, tax_rate=0, subtotal_amount=0, tax_amount=0,
        total_amount=800, valid_until=date(2026, 12, 31),
    ))
    db_session.add(WorkHourLog(
        project_id=data["project"].id, hours_spent=Decimal("8"),
        log_date=datetime(2026, 4, 1), task_description="开发",
        created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
    ))
    await db_session.commit()

    result = await get_project_labor_cost(db_session, data["project"].id)
    # (8 / HOURS_PER_DAY) * 800 = 800
    assert result["labor_cost"] == Decimal("800")
    assert HOURS_PER_DAY == 8  # 常量值为 8


@pytest.mark.asyncio
async def test_v19_profit_complete_data(db_session: AsyncSession):
    """v1.9: 完整数据时返回完整报告"""
    data = await _create_test_data(db_session)
    # 报价单（提供 daily_rate）
    db_session.add(Quotation(
        quote_no="BJ-V19-004", customer_id=data["customer"].id,
        project_id=data["project"].id, title="完整数据报价",
        requirement_summary="测试", estimate_days=10, estimate_hours=80,
        daily_rate=Decimal("1000"), direct_cost=0, risk_buffer_rate=0,
        discount_amount=0, tax_rate=0, subtotal_amount=0, tax_amount=0,
        total_amount=10000, valid_until=date(2026, 12, 31),
    ))
    # 工时
    db_session.add(WorkHourLog(
        project_id=data["project"].id, hours_spent=Decimal("40"),
        log_date=datetime(2026, 4, 1), task_description="开发",
        created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
    ))
    # 收入
    db_session.add(FinanceRecord(
        type="income", amount=30000, date=date(2026, 4, 1),
        status="confirmed", contract_id=data["contract"].id,
    ))
    # 固定成本
    db_session.add(FixedCost(
        name="服务器费用", category="cloud", amount=Decimal("500"),
        period="monthly", effective_date=date(2026, 4, 1),
        project_id=data["project"].id,
    ))
    # 进项发票
    db_session.add(InputInvoice(
        invoice_no="IN-001", vendor_name="测试供应商",
        invoice_date=date(2026, 4, 1), amount_excluding_tax=Decimal("1000"),
        tax_rate=Decimal("0.13"), tax_amount=Decimal("130"),
        total_amount=Decimal("1130"), category="software",
        project_id=data["project"].id,
    ))
    await db_session.commit()

    report = await calculate_project_profit_v19(db_session, data["project"].id)
    assert "error" not in report
    assert report["project_id"] == data["project"].id
    assert report["revenue"]["received_amount"] == 30000.0
    assert report["cost"]["labor_cost"] == 5000.0  # (40/8)*1000
    assert report["cost"]["fixed_cost_allocated"] == 500.0
    assert report["cost"]["input_invoice_cost"] == 1130.0
    assert report["cost"]["hours_per_day"] == HOURS_PER_DAY
    assert len(report["warnings"]) == 0


@pytest.mark.asyncio
async def test_v19_profit_warning_no_hours(db_session: AsyncSession):
    """v1.9: 无工时记录时包含 warning"""
    data = await _create_test_data(db_session)
    db_session.add(Quotation(
        quote_no="BJ-V19-005", customer_id=data["customer"].id,
        project_id=data["project"].id, title="无工时报价",
        requirement_summary="测试", estimate_days=5,
        daily_rate=Decimal("1000"), direct_cost=0, risk_buffer_rate=0,
        discount_amount=0, tax_rate=0, subtotal_amount=0, tax_amount=0,
        total_amount=5000, valid_until=date(2026, 12, 31),
    ))
    await db_session.commit()

    report = await calculate_project_profit_v19(db_session, data["project"].id)
    assert "error" not in report
    assert "无工时记录" in report["warnings"]


@pytest.mark.asyncio
async def test_v19_profit_warning_no_daily_rate(db_session: AsyncSession):
    """v1.9: 有工时无 daily_rate 时包含 warning"""
    data = await _create_test_data(db_session)
    db_session.add(WorkHourLog(
        project_id=data["project"].id, hours_spent=Decimal("16"),
        log_date=datetime(2026, 4, 1), task_description="开发",
        created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
    ))
    await db_session.commit()

    report = await calculate_project_profit_v19(db_session, data["project"].id)
    assert "error" not in report
    assert "关联报价单无 daily_rate" in report["warnings"]


@pytest.mark.asyncio
async def test_v19_profit_project_not_found(db_session: AsyncSession):
    """v1.9: 项目不存在时返回 error"""
    report = await calculate_project_profit_v19(db_session, 99999)
    assert report == {"error": "project not found"}


@pytest.mark.asyncio
async def test_v19_refresh_cache_success(db_session: AsyncSession):
    """v1.9: 刷新缓存成功"""
    data = await _create_test_data(db_session)
    db_session.add(Quotation(
        quote_no="BJ-V19-006", customer_id=data["customer"].id,
        project_id=data["project"].id, title="缓存测试报价",
        requirement_summary="测试", estimate_days=5, estimate_hours=40,
        daily_rate=Decimal("1000"), direct_cost=0, risk_buffer_rate=0,
        discount_amount=0, tax_rate=0, subtotal_amount=0, tax_amount=0,
        total_amount=5000, valid_until=date(2026, 12, 31),
    ))
    db_session.add(WorkHourLog(
        project_id=data["project"].id, hours_spent=Decimal("40"),
        log_date=datetime(2026, 4, 1), task_description="开发",
        created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
    ))
    db_session.add(FinanceRecord(
        type="income", amount=20000, date=date(2026, 4, 1),
        status="confirmed", contract_id=data["contract"].id,
    ))
    await db_session.commit()

    report = await refresh_project_profit_cache(db_session, data["project"].id)
    assert "error" not in report

    # 验证缓存已写入
    stmt = select(Project).where(Project.id == data["project"].id)
    result = await db_session.execute(stmt)
    project = result.scalar_one()
    assert project.cached_revenue == Decimal("20000")
    assert project.cached_labor_cost == Decimal("5000")
    assert project.cached_fixed_cost == Decimal("0")
    assert project.cached_input_cost == Decimal("0")
    assert project.profit_cache_updated_at is not None


@pytest.mark.asyncio
async def test_v19_refresh_cache_project_not_found(db_session: AsyncSession):
    """v1.9: 项目不存在时返回 error"""
    report = await refresh_project_profit_cache(db_session, 99999)
    assert report == {"error": "project not found"}


@pytest.mark.asyncio
async def test_v19_overview_with_cached_and_uncached(db_session: AsyncSession):
    """v1.9: 概览列表同时返回缓存和实时计算的项目"""
    # 项目1：有缓存
    data1 = await _create_test_data(db_session)
    data1["project"].cached_revenue = Decimal("10000")
    data1["project"].cached_labor_cost = Decimal("2000")
    data1["project"].cached_fixed_cost = Decimal("500")
    data1["project"].cached_input_cost = Decimal("300")
    data1["project"].cached_gross_profit = Decimal("7200")
    data1["project"].cached_gross_margin = Decimal("0.72")
    data1["project"].profit_cache_updated_at = datetime(2026, 4, 1)
    await db_session.commit()

    # 项目2：无缓存，实时计算
    customer2 = Customer(name="客户2", contact_person="李四", phone="13800000002")
    db_session.add(customer2)
    await db_session.commit()
    await db_session.refresh(customer2)
    project2 = Project(name="实时计算项目", customer_id=customer2.id, status="executing")
    db_session.add(project2)
    await db_session.commit()
    await db_session.refresh(project2)

    overview = await get_profit_overview(db_session)
    assert len(overview) >= 2

    # 找到缓存项目
    cached = [o for o in overview if o["project_id"] == data1["project"].id]
    assert len(cached) == 1
    assert cached[0]["cached_at"] is not None
    assert cached[0]["gross_profit"] == 7200.0

    # 找到实时项目
    realtime = [o for o in overview if o["project_id"] == project2.id]
    assert len(realtime) == 1
    assert realtime[0]["cached_at"] is None


@pytest.mark.asyncio
async def test_v19_profit_api_endpoint(client: AsyncClient):
    """v1.9: /projects/{id}/profit API 端点正常返回"""
    h = await _auth(client)

    # 创建客户
    resp = await client.post("/api/v1/customers", json={
        "name": "v19 API测试客户", "contact_person": "张三", "phone": "13700000010",
    }, headers=h)
    assert resp.status_code == 201
    customer_id = resp.json()["id"]

    # 创建项目
    resp = await client.post("/api/v1/projects", json={
        "name": "v19 API测试项目", "customer_id": customer_id,
    }, headers=h)
    assert resp.status_code == 201
    project_id = resp.json()["id"]

    # 创建报价单（提供 daily_rate）
    resp = await client.post("/api/v1/quotations", json={
        "customer_id": customer_id,
        "project_id": project_id,
        "title": "API测试报价",
        "requirement_summary": "测试需求",
        "estimate_days": 10,
        "estimate_hours": 80,
        "daily_rate": 1000,
        "direct_cost": 0,
        "risk_buffer_rate": 0,
        "discount_amount": 0,
        "tax_rate": 0,
        "subtotal_amount": 10000,
        "tax_amount": 0,
        "total_amount": 10000,
        "valid_until": "2026-12-31",
    }, headers=h)
    assert resp.status_code == 201

    # 调用 v1.9 利润 API
    resp = await client.get(f"/api/v1/projects/{project_id}/profit", headers=h)
    assert resp.status_code == 200
    body = resp.json()
    assert body["project_id"] == project_id
    assert "revenue" in body
    assert "cost" in body
    assert "profit" in body
    assert "warnings" in body


@pytest.mark.asyncio
async def test_v19_profit_api_project_not_found(client: AsyncClient):
    """v1.9: 不存在的项目返回 404"""
    h = await _auth(client)
    resp = await client.get("/api/v1/projects/99999/profit", headers=h)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_v19_refresh_cache_api(client: AsyncClient):
    """v1.9: POST /projects/{id}/profit/refresh API"""
    h = await _auth(client)

    resp = await client.post("/api/v1/customers", json={
        "name": "刷新API客户", "contact_person": "王五", "phone": "13700000011",
    }, headers=h)
    customer_id = resp.json()["id"]

    resp = await client.post("/api/v1/projects", json={
        "name": "刷新API项目", "customer_id": customer_id,
    }, headers=h)
    project_id = resp.json()["id"]

    resp = await client.post(f"/api/v1/projects/{project_id}/profit/refresh", headers=h)
    assert resp.status_code == 200
    body = resp.json()
    assert "profit" in body


@pytest.mark.asyncio
async def test_v19_profit_overview_api(client: AsyncClient):
    """v1.9: GET /finance/profit-overview API"""
    h = await _auth(client)
    resp = await client.get("/api/v1/finance/profit-overview", headers=h)
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
