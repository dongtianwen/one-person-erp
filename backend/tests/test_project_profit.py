"""FR-401 项目利润核算测试。"""
import pytest
from datetime import date
from decimal import Decimal
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.project import Project
from app.models.contract import Contract
from app.models.finance import FinanceRecord
from app.core.profit_utils import (
    calculate_project_income,
    calculate_project_cost,
    calculate_project_profit,
)


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
    """FR-401: 利润接口返回结构符合规范"""
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
    assert "income" in body
    assert "cost" in body
    assert "profit" in body
    assert "profit_margin" in body
    assert "currency" in body
    assert body["currency"] == "CNY"


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
