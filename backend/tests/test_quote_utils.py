"""v1.6 报价金额计算与工具函数测试——FR-602"""
import pytest
from decimal import Decimal

from app.core.quote_utils import (
    calculate_quote_amount,
    can_edit_quote,
    can_delete_quote,
    build_quote_preview,
)


class TestCalculateQuoteAmount:
    """FR-602: 金额计算测试。"""

    def test_calculate_quote_amount_basic(self):
        """FR-602: 基本金额计算。"""
        result = calculate_quote_amount(
            estimate_days=10,
            daily_rate=Decimal("1000"),
            direct_cost=Decimal("5000"),
            risk_buffer_rate=Decimal("0.1"),
            discount_amount=Decimal("1000"),
            tax_rate=Decimal("0.06"),
        )
        assert result["labor_amount"] == Decimal("10000")
        assert result["base_amount"] == Decimal("15000")
        assert result["buffer_amount"] == Decimal("1500")
        assert result["subtotal_amount"] == Decimal("16500")
        assert result["tax_amount"] == Decimal("990")
        assert result["total_amount"] == Decimal("16490")

    def test_calculate_quote_amount_without_daily_rate(self):
        """FR-602: daily_rate 为空时 labor_amount 为 0。"""
        result = calculate_quote_amount(
            estimate_days=10,
            daily_rate=None,
            direct_cost=Decimal("5000"),
            risk_buffer_rate=Decimal("0"),
            discount_amount=Decimal("0"),
            tax_rate=Decimal("0"),
        )
        assert result["labor_amount"] == Decimal("0")
        assert result["base_amount"] == Decimal("5000")

    def test_calculate_quote_amount_without_direct_cost(self):
        """FR-602: direct_cost 为空按 0 处理。"""
        result = calculate_quote_amount(
            estimate_days=10,
            daily_rate=Decimal("1000"),
            direct_cost=None,
            risk_buffer_rate=Decimal("0"),
            discount_amount=Decimal("0"),
            tax_rate=Decimal("0"),
        )
        assert result["labor_amount"] == Decimal("10000")
        assert result["base_amount"] == Decimal("10000")

    def test_calculate_quote_amount_precision_two_decimal(self):
        """FR-602: 所有金额四舍五入到 2 位小数。"""
        result = calculate_quote_amount(
            estimate_days=7,
            daily_rate=Decimal("333.33"),
            direct_cost=Decimal("0"),
            risk_buffer_rate=Decimal("0.15"),
            discount_amount=Decimal("0"),
            tax_rate=Decimal("0.13"),
        )
        for key, val in result.items():
            # 检查最多 2 位小数
            assert val == val.quantize(Decimal("0.01")), f"{key} 精度超过 2 位"

    def test_calculate_quote_amount_no_negative_total(self):
        """FR-602: 总价不允许为负数。"""
        with pytest.raises(ValueError, match="负数"):
            calculate_quote_amount(
                estimate_days=1,
                daily_rate=Decimal("100"),
                direct_cost=Decimal("0"),
                risk_buffer_rate=Decimal("0"),
                discount_amount=Decimal("200"),
                tax_rate=Decimal("0"),
            )


class TestBuildQuotePreview:
    """FR-602: 预览计算测试。"""

    def test_build_quote_preview_success(self):
        """FR-602: 预览返回完整金额。"""
        payload = {
            "estimate_days": 5,
            "daily_rate": Decimal("1000"),
            "direct_cost": Decimal("0"),
            "risk_buffer_rate": Decimal("0"),
            "discount_amount": Decimal("0"),
            "tax_rate": Decimal("0"),
        }
        result = build_quote_preview(payload)
        assert result["labor_amount"] == Decimal("5000")
        assert result["total_amount"] == Decimal("5000")

    def test_build_quote_preview_matches_save_logic(self):
        """FR-602: 预览与正式保存使用同一套计算逻辑。"""
        payload = {
            "estimate_days": 10,
            "daily_rate": Decimal("800"),
            "direct_cost": Decimal("2000"),
            "risk_buffer_rate": Decimal("0.05"),
            "discount_amount": Decimal("500"),
            "tax_rate": Decimal("0.06"),
        }
        preview = build_quote_preview(payload)
        direct = calculate_quote_amount(
            estimate_days=10,
            daily_rate=Decimal("800"),
            direct_cost=Decimal("2000"),
            risk_buffer_rate=Decimal("0.05"),
            discount_amount=Decimal("500"),
            tax_rate=Decimal("0.06"),
        )
        assert preview == direct


class TestCanEditDelete:
    """FR-602: 编辑/删除权限判断。"""

    def test_can_edit_draft(self):
        class MockQuote:
            status = "draft"
        assert can_edit_quote(MockQuote()) is True

    def test_can_edit_sent(self):
        class MockQuote:
            status = "sent"
        assert can_edit_quote(MockQuote()) is True

    def test_cannot_edit_accepted(self):
        class MockQuote:
            status = "accepted"
        assert can_edit_quote(MockQuote()) is False

    def test_can_delete_draft(self):
        class MockQuote:
            status = "draft"
        assert can_delete_quote(MockQuote()) is True

    def test_cannot_delete_accepted(self):
        class MockQuote:
            status = "accepted"
        assert can_delete_quote(MockQuote()) is False

    def test_cannot_delete_expired(self):
        class MockQuote:
            status = "expired"
        assert can_delete_quote(MockQuote()) is False
