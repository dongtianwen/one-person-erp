"""v1.3 财务工具函数——税额计算、季度统计。"""

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from app.core.constants import (
    DECIMAL_PLACES,
    INVOICE_DIRECTION_OUTPUT,
    INVOICE_DIRECTION_INPUT,
    INVOICE_TYPE_SPECIAL,
)


def calculate_tax_amount(amount, tax_rate) -> Decimal:
    """
    计算税额，四舍五入到 2 位小数。
    tax_amount = round(amount * tax_rate, 2)

    参数和返回值均为 Decimal 类型，禁止使用 float 计算。
    """
    amount = Decimal(str(amount))
    tax_rate = Decimal(str(tax_rate))
    result = amount * tax_rate
    return result.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def get_quarter_date_range(year: int, quarter: int) -> tuple[date, date]:
    """
    返回季度起始日和结束日（均为 date 对象）。

    示例：get_quarter_date_range(2026, 1) -> (date(2026,1,1), date(2026,3,31))
    """
    quarter_starts: dict[int, tuple[int, int]] = {
        1: (1, 31),
        2: (4, 30),
        3: (7, 31),
        4: (10, 31),
    }
    if quarter not in quarter_starts:
        raise ValueError(f"无效的季度: {quarter}, 必须为 1-4")

    start_month, end_day = quarter_starts[quarter]
    end_month = start_month + 2

    start = date(year, start_month, 1)
    end = date(year, end_month, end_day)
    return (start, end)
