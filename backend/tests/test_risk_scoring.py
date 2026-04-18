"""v2.2 风险评分引擎测试。"""
import pytest
from app.core.agent_rules import (
    _calculate_overdue_risk_score,
    _calculate_profit_risk_score,
    _calculate_cashflow_risk_score,
)


class TestOverdueRiskScore:
    """逾期回款风险评分测试。"""

    def test_minimal_risk(self):
        result = _calculate_overdue_risk_score(
            max_days_overdue=1,
            total_overdue_amount=5000,
            contract_amount=1000000,
            customer_risk_level="normal",
            acceptance_pending=False,
            invoice_unsigned=False,
        )
        assert result["total_score"] <= 25
        assert result["days_overdue_score"] >= 1
        assert result["amount_score"] >= 1

    def test_high_days_overdue(self):
        result = _calculate_overdue_risk_score(
            max_days_overdue=90,
            total_overdue_amount=50000,
            contract_amount=500000,
            customer_risk_level="normal",
            acceptance_pending=False,
            invoice_unsigned=False,
        )
        assert result["days_overdue_score"] == 25
        assert result["total_score"] >= 30

    def test_high_amount(self):
        result = _calculate_overdue_risk_score(
            max_days_overdue=30,
            total_overdue_amount=1_000_000,
            contract_amount=2_000_000,
            customer_risk_level="normal",
            acceptance_pending=False,
            invoice_unsigned=False,
        )
        assert result["amount_score"] == 20
        assert result["amount_ratio_score"] == 20

    def test_customer_risk_high(self):
        result = _calculate_overdue_risk_score(
            max_days_overdue=10,
            total_overdue_amount=50000,
            contract_amount=200000,
            customer_risk_level="high",
            acceptance_pending=False,
            invoice_unsigned=False,
        )
        assert result["customer_risk_score"] == 15

    def test_customer_risk_elevated(self):
        result = _calculate_overdue_risk_score(
            max_days_overdue=10,
            total_overdue_amount=50000,
            contract_amount=200000,
            customer_risk_level="elevated",
            acceptance_pending=False,
            invoice_unsigned=False,
        )
        assert result["customer_risk_score"] == 8

    def test_acceptance_pending_adds_risk(self):
        result = _calculate_overdue_risk_score(
            max_days_overdue=10,
            total_overdue_amount=50000,
            contract_amount=200000,
            customer_risk_level="normal",
            acceptance_pending=True,
            invoice_unsigned=False,
        )
        assert result["acceptance_status_score"] == 10

    def test_invoice_unsigned_adds_risk(self):
        result = _calculate_overdue_risk_score(
            max_days_overdue=10,
            total_overdue_amount=50000,
            contract_amount=200000,
            customer_risk_level="normal",
            acceptance_pending=False,
            invoice_unsigned=True,
        )
        assert result["invoice_status_score"] == 10

    def test_all_high_max_100(self):
        result = _calculate_overdue_risk_score(
            max_days_overdue=90,
            total_overdue_amount=1_000_000,
            contract_amount=1_000_000,
            customer_risk_level="high",
            acceptance_pending=True,
            invoice_unsigned=True,
        )
        assert result["total_score"] == 100
        assert "total_score" in result
        assert "days_overdue_score" in result
        assert "amount_score" in result
        assert "amount_ratio_score" in result
        assert "customer_risk_score" in result
        assert "acceptance_status_score" in result
        assert "invoice_status_score" in result

    def test_zero_contract_amount(self):
        result = _calculate_overdue_risk_score(
            max_days_overdue=10,
            total_overdue_amount=50000,
            contract_amount=0,
            customer_risk_level="normal",
            acceptance_pending=False,
            invoice_unsigned=False,
        )
        assert result["amount_ratio_score"] == 10


class TestProfitRiskScore:
    """利润率异常风险评分测试。"""

    def test_healthy_margin(self):
        result = _calculate_profit_risk_score(margin_percent=5)
        assert result["total_score"] <= 20
        assert result["negative_margin_bonus"] == 0

    def test_low_margin(self):
        result = _calculate_profit_risk_score(margin_percent=5)
        assert result["total_score"] >= 10

    def test_negative_margin(self):
        result = _calculate_profit_risk_score(margin_percent=-15)
        assert result["total_score"] >= 30
        assert result["negative_margin_bonus"] == 20

    def test_large_loss(self):
        result = _calculate_profit_risk_score(margin_percent=-55)
        assert result["total_score"] == 80

    def test_score_breakdown_present(self):
        result = _calculate_profit_risk_score(margin_percent=-30)
        assert "total_score" in result
        assert "margin_severity_score" in result
        assert "negative_margin_bonus" in result


class TestCashflowRiskScore:
    """现金流风险评分测试。"""

    def test_positive_cashflow_no_risk(self):
        result = _calculate_cashflow_risk_score(
            total_cashflow=500000,
            weeks_horizon=4,
        )
        assert result["total_score"] == 0

    def test_negative_cashflow_short_period(self):
        result = _calculate_cashflow_risk_score(
            total_cashflow=-500000,
            weeks_horizon=2,
        )
        assert result["total_score"] >= 40
        assert result["time_score"] == 30

    def test_negative_cashflow_long_period(self):
        result = _calculate_cashflow_risk_score(
            total_cashflow=-200000,
            weeks_horizon=12,
        )
        assert result["total_score"] >= 30
        assert result["time_score"] == 10

    def test_urgent_threshold(self):
        result = _calculate_cashflow_risk_score(
            total_cashflow=-600000,
            weeks_horizon=4,
            urgent_threshold=-500000,
        )
        assert result["urgency_bonus"] == 20

    def test_score_breakdown_present(self):
        result = _calculate_cashflow_risk_score(
            total_cashflow=-300000,
            weeks_horizon=6,
        )
        assert "total_score" in result
        assert "magnitude_score" in result
        assert "time_score" in result
        assert "urgency_bonus" in result
