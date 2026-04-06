"""FR-303 发票台账测试——字段校验 + 税额计算 + 季度统计。"""

import pytest
from app.core.finance_utils import calculate_tax_amount, get_quarter_date_range


async def _auth(client) -> dict:
    r = await client.post("/api/v1/auth/login", data={"username": "admin", "password": "admin123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# --- 簇 C: 发票字段校验 + 税额计算 ---


async def test_tax_amount_calculated_by_backend(client):
    """tax_amount 由后端计算"""
    h = await _auth(client)
    r = await client.post("/api/v1/finances", json={
        "type": "income", "amount": 10000, "date": "2026-04-01",
        "invoice_no": "INV-TAX-001",
        "invoice_direction": "output",
        "invoice_type": "special",
        "tax_rate": 0.06,
    }, headers=h)
    assert r.status_code == 201
    data = r.json()
    assert data["tax_amount"] is not None
    assert float(data["tax_amount"]) == 600.00


async def test_tax_amount_precision_two_decimal_places():
    """税额精度为 2 位小数"""
    from decimal import Decimal
    result = calculate_tax_amount(333.33, 0.13)
    assert result == Decimal("43.33")


async def test_invoice_direction_required_when_invoice_no_present(client):
    """有发票号码但缺少发票方向 → 422"""
    h = await _auth(client)
    r = await client.post("/api/v1/finances", json={
        "type": "income", "amount": 1000, "date": "2026-04-01",
        "invoice_no": "INV-DIR-001",
        "invoice_type": "general",
        "tax_rate": 0.06,
    }, headers=h)
    assert r.status_code == 422
    assert "填写发票号码时必须填写发票方向" in r.json()["detail"]


async def test_invoice_type_required_when_invoice_no_present(client):
    """有发票号码但缺少发票类型 → 422"""
    h = await _auth(client)
    r = await client.post("/api/v1/finances", json={
        "type": "income", "amount": 1000, "date": "2026-04-01",
        "invoice_no": "INV-TYPE-001",
        "invoice_direction": "output",
        "tax_rate": 0.06,
    }, headers=h)
    assert r.status_code == 422
    assert "填写发票号码时必须填写发票类型" in r.json()["detail"]


async def test_tax_rate_required_when_invoice_no_present(client):
    """有发票号码但缺少税率 → 422"""
    h = await _auth(client)
    r = await client.post("/api/v1/finances", json={
        "type": "income", "amount": 1000, "date": "2026-04-01",
        "invoice_no": "INV-RATE-001",
        "invoice_direction": "output",
        "invoice_type": "general",
    }, headers=h)
    assert r.status_code == 422
    assert "填写发票号码时必须填写税率" in r.json()["detail"]


async def test_invoice_no_empty_clears_all_invoice_fields(client):
    """无发票号码时发票字段强制置 NULL"""
    h = await _auth(client)
    r = await client.post("/api/v1/finances", json={
        "type": "expense", "amount": 3000, "date": "2026-04-01",
        "funding_source": "company_account",
        "invoice_direction": "output",
        "invoice_type": "general",
        "tax_rate": 0.06,
    }, headers=h)
    assert r.status_code == 201
    data = r.json()
    assert data["invoice_direction"] is None
    assert data["invoice_type"] is None
    assert data["tax_rate"] is None
    assert data["tax_amount"] is None


async def test_update_clearing_invoice_no_also_clears_invoice_fields(client):
    """更新时清空发票号码，四个发票字段同步清空"""
    h = await _auth(client)
    # 先创建有发票的记录
    r = await client.post("/api/v1/finances", json={
        "type": "income", "amount": 10000, "date": "2026-04-01",
        "invoice_no": "INV-CLR-001",
        "invoice_direction": "output",
        "invoice_type": "general",
        "tax_rate": 0.06,
    }, headers=h)
    rid = r.json()["id"]
    assert r.json()["tax_amount"] is not None

    # 清空发票号码
    r2 = await client.put(f"/api/v1/finances/{rid}", json={
        "invoice_no": None,
    }, headers=h)
    assert r2.status_code == 200
    data = r2.json()
    assert data["invoice_direction"] is None
    assert data["invoice_type"] is None
    assert data["tax_rate"] is None
    assert data["tax_amount"] is None


# --- 簇 D: 季度统计 ---


async def test_get_quarter_date_range_q1():
    """Q1 日期边界"""
    start, end = get_quarter_date_range(2026, 1)
    assert start.year == 2026 and start.month == 1 and start.day == 1
    assert end.year == 2026 and end.month == 3 and end.day == 31


async def test_get_quarter_date_range_q4():
    """Q4 日期边界"""
    start, end = get_quarter_date_range(2026, 4)
    assert start.year == 2026 and start.month == 10 and start.day == 1
    assert end.year == 2026 and end.month == 12 and end.day == 31


async def test_quarterly_invalid_quarter_returns_422(client):
    """无效季度 → 422"""
    h = await _auth(client)
    r = await client.get("/api/v1/finances/tax-summary?year=2026&quarter=5", headers=h)
    assert r.status_code == 422


async def test_quarterly_empty_quarter_returns_zero_http200(client):
    """空季度返回全零 HTTP 200"""
    h = await _auth(client)
    r = await client.get("/api/v1/finances/tax-summary?year=2026&quarter=1", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert data["output_tax_total"] == 0.00
    assert data["input_tax_total"] == 0.00
    assert data["tax_payable"] == 0.00


async def test_quarterly_output_tax_includes_all_output_records(client):
    """季度统计——output 方向全量计入"""
    h = await _auth(client)
    for i in range(3):
        await client.post("/api/v1/finances", json={
            "type": "income", "amount": 10000, "date": "2026-01-15",
            "invoice_no": f"INV-OUT-{i}",
            "invoice_direction": "output",
            "invoice_type": "special",
            "tax_rate": 0.06,
        }, headers=h)

    r = await client.get("/api/v1/finances/tax-summary?year=2026&quarter=1", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert data["output_tax_total"] == 1800.00  # 600 * 3
    assert data["record_count"]["output"] == 3


async def test_quarterly_input_tax_includes_only_special_invoices(client):
    """季度统计——进项只计入专用发票"""
    h = await _auth(client)
    # 专用发票
    await client.post("/api/v1/finances", json={
        "type": "expense", "amount": 5000, "date": "2026-02-10",
        "funding_source": "company_account",
        "invoice_no": "INV-IN-SPEC",
        "invoice_direction": "input",
        "invoice_type": "special",
        "tax_rate": 0.13,
    }, headers=h)
    # 普通发票
    await client.post("/api/v1/finances", json={
        "type": "expense", "amount": 3000, "date": "2026-02-10",
        "funding_source": "company_account",
        "invoice_no": "INV-IN-GEN",
        "invoice_direction": "input",
        "invoice_type": "general",
        "tax_rate": 0.06,
    }, headers=h)

    r = await client.get("/api/v1/finances/tax-summary?year=2026&quarter=1", headers=h)
    data = r.json()
    assert data["input_tax_total"] == 650.00  # 5000 * 0.13
    assert data["record_count"]["input"] == 1  # only special


async def test_quarterly_input_tax_excludes_general_invoices(client):
    """季度统计——普通发票不计入进项"""
    h = await _auth(client)
    await client.post("/api/v1/finances", json={
        "type": "expense", "amount": 5000, "date": "2026-01-10",
        "funding_source": "company_account",
        "invoice_no": "INV-GEN-ONLY",
        "invoice_direction": "input",
        "invoice_type": "general",
        "tax_rate": 0.06,
    }, headers=h)

    r = await client.get("/api/v1/finances/tax-summary?year=2026&quarter=1", headers=h)
    data = r.json()
    assert data["input_tax_total"] == 0.00


async def test_quarterly_input_tax_excludes_electronic_invoices(client):
    """季度统计——电子发票不计入进项"""
    h = await _auth(client)
    await client.post("/api/v1/finances", json={
        "type": "expense", "amount": 5000, "date": "2026-01-10",
        "funding_source": "company_account",
        "invoice_no": "INV-ELEC-ONLY",
        "invoice_direction": "input",
        "invoice_type": "electronic",
        "tax_rate": 0.06,
    }, headers=h)

    r = await client.get("/api/v1/finances/tax-summary?year=2026&quarter=1", headers=h)
    data = r.json()
    assert data["input_tax_total"] == 0.00


async def test_quarterly_tax_payable_equals_output_minus_input(client):
    """应纳税额 = 销项 - 进项"""
    h = await _auth(client)
    # 销项
    await client.post("/api/v1/finances", json={
        "type": "income", "amount": 20000, "date": "2026-02-01",
        "invoice_no": "INV-OUT-PAYABLE",
        "invoice_direction": "output",
        "invoice_type": "special",
        "tax_rate": 0.06,
    }, headers=h)
    # 进项（专用发票）
    await client.post("/api/v1/finances", json={
        "type": "expense", "amount": 10000, "date": "2026-02-01",
        "funding_source": "company_account",
        "invoice_no": "INV-IN-PAYABLE",
        "invoice_direction": "input",
        "invoice_type": "special",
        "tax_rate": 0.13,
    }, headers=h)

    r = await client.get("/api/v1/finances/tax-summary?year=2026&quarter=1", headers=h)
    data = r.json()
    assert data["output_tax_total"] == 1200.00
    assert data["input_tax_total"] == 1300.00
    assert data["tax_payable"] == -100.00  # 留抵


async def test_quarterly_response_structure_exact_match(client):
    """季度统计响应结构严格匹配"""
    h = await _auth(client)
    r = await client.get("/api/v1/finances/tax-summary?year=2026&quarter=1", headers=h)
    data = r.json()
    assert "year" in data
    assert "quarter" in data
    assert "output_tax_total" in data
    assert "input_tax_total" in data
    assert "tax_payable" in data
    assert "record_count" in data
    assert "output" in data["record_count"]
    assert "input" in data["record_count"]
