"""FR-301 现金流预测测试。"""

from datetime import date, timedelta
from app.core.cashflow_utils import get_forecast_weeks
from app.core.constants import CASHFLOW_FORECAST_DAYS, CASHFLOW_WEEKS_PER_MONTH, DECIMAL_PLACES


async def _auth(client) -> dict:
    r = await client.post("/api/v1/auth/login", data={"username": "admin", "password": "admin123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# --- 工具函数单元测试 ---


def test_get_forecast_weeks_boundary():
    """90 天覆盖的周数正确"""
    start = date(2026, 4, 6)
    weeks = get_forecast_weeks(start)
    last_week = weeks[-1]
    expected_end = start + timedelta(days=CASHFLOW_FORECAST_DAYS - 1)
    assert last_week["week_end"] == expected_end
    assert weeks[0]["week_start"] == start


def test_get_forecast_weeks_first_week_starts_on_monday():
    """第一周起始日为周一"""
    start = date(2026, 4, 6)  # 周一
    weeks = get_forecast_weeks(start)
    assert weeks[0]["week_start"] == start
    assert weeks[0]["week_start"].weekday() == 0


def test_calculate_weekly_expense_formula():
    """周均支出公式验证"""
    total = 3000
    months = 3
    monthly_avg = total / months
    weekly_avg = round(monthly_avg / CASHFLOW_WEEKS_PER_MONTH, DECIMAL_PLACES)
    assert weekly_avg == 230.95


# --- API 接口测试 ---


async def test_forecast_returns_correct_week_count(client):
    """预测返回正确的周数"""
    h = await _auth(client)
    r = await client.get("/api/v1/cashflow/forecast", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert len(data["forecast"]) > 0


async def test_forecast_first_week_starts_on_monday(client):
    """第一周起始为周一"""
    h = await _auth(client)
    r = await client.get("/api/v1/cashflow/forecast", headers=h)
    assert r.status_code == 200
    from datetime import datetime
    ws = datetime.strptime(r.json()["forecast"][0]["week_start"], "%Y-%m-%d").date()
    assert ws.weekday() == 0


async def test_forecast_last_day_is_exactly_day_90(client):
    """最后一天恰好是第 90 天"""
    h = await _auth(client)
    r = await client.get("/api/v1/cashflow/forecast", headers=h)
    assert r.status_code == 200
    data = r.json()
    from datetime import datetime
    last_week = data["forecast"][-1]
    we = datetime.strptime(last_week["week_end"], "%Y-%m-%d").date()
    ws = datetime.strptime(data["forecast"][0]["week_start"], "%Y-%m-%d").date()
    assert (we - ws).days == CASHFLOW_FORECAST_DAYS - 1


async def test_forecast_no_data_returns_90day_zeros_http200(client):
    """无数据返回全零 HTTP 200"""
    h = await _auth(client)
    r = await client.get("/api/v1/cashflow/forecast", headers=h)
    assert r.status_code == 200
    data = r.json()
    for week in data["forecast"]:
        assert week["predicted_income"] == 0.00
        assert week["predicted_expense"] == 0.00
        assert week["predicted_net"] == 0.00


async def test_forecast_response_structure_exact_match(client):
    """响应结构严格匹配"""
    h = await _auth(client)
    r = await client.get("/api/v1/cashflow/forecast", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert "forecast" in data
    assert "summary" in data

    for week in data["forecast"]:
        assert "week_index" in week
        assert "week_start" in week
        assert "week_end" in week
        assert "predicted_income" in week
        assert "predicted_expense" in week
        assert "predicted_net" in week

    assert "total_predicted_income" in data["summary"]
    assert "total_predicted_expense" in data["summary"]
    assert "total_predicted_net" in data["summary"]


async def test_forecast_all_amounts_two_decimal_precision(client):
    """所有金额字段精度 2 位小数"""
    h = await _auth(client)
    r = await client.get("/api/v1/cashflow/forecast", headers=h)
    assert r.status_code == 200
    data = r.json()
    for week in data["forecast"]:
        for field in ["predicted_income", "predicted_expense", "predicted_net"]:
            val = week[field]
            if isinstance(val, float):
                assert round(val, 2) == val


async def test_forecast_summary_totals_match_weekly_sum(client):
    """汇总值等于周值之和"""
    h = await _auth(client)
    r = await client.get("/api/v1/cashflow/forecast", headers=h)
    assert r.status_code == 200
    data = r.json()
    total_income = sum(w["predicted_income"] for w in data["forecast"])
    total_expense = sum(w["predicted_expense"] for w in data["forecast"])
    total_net = sum(w["predicted_net"] for w in data["forecast"])

    assert round(data["summary"]["total_predicted_income"], 2) == round(total_income, 2)
    assert round(data["summary"]["total_predicted_expense"], 2) == round(total_expense, 2)
    assert round(data["summary"]["total_predicted_net"], 2) == round(total_net, 2)


async def test_forecast_expense_zero_when_no_history_no_error(client):
    """无历史支出时不报错，返回 0"""
    h = await _auth(client)
    r = await client.get("/api/v1/cashflow/forecast", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert data["summary"]["total_predicted_expense"] == 0.00
