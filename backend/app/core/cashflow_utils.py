"""v1.3 现金流预测工具函数。"""

from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from app.core.constants import (
    CASHFLOW_FORECAST_DAYS,
    CASHFLOW_WEEKS_PER_MONTH,
    CASHFLOW_HISTORY_MONTHS,
    CASHFLOW_CONTRACT_STATUSES,
    DECIMAL_PLACES,
    WEEK_START_DAY,
)


def get_forecast_weeks(start_date: date | str) -> list[dict]:
    """
    生成未来 90 天的自然周列表。

    - 从 start_date（含）起连续 90 个自然日，包含第 1 天和第 90 天
    - 按自然周（周一起始）分组
    - 最后一周不足 7 天时，week_end 取第 90 天
    - 返回：[{"week_index": 1, "week_start": date, "week_end": date}, ...]
    """
    if isinstance(start_date, str):
        start_date = date.fromisoformat(start_date)
    end_date = start_date + timedelta(days=CASHFLOW_FORECAST_DAYS - 1)
    current_date = start_date
    weeks: list[dict] = []
    week_index = 0

    while current_date <= end_date:
        # 找到当前日期所在周的周一
        days_since_monday = current_date.weekday() - WEEK_START_DAY
        if days_since_monday < 0:
            days_since_monday += 7
        week_start = current_date - timedelta(days=days_since_monday)

        # 如果 week_start 早于 start_date，调整
        if week_start < start_date:
            week_start = start_date

        # 计算这一周的结束日（周日）
        week_end = week_start + timedelta(days=6 - (week_start.weekday() - WEEK_START_DAY) % 7)
        # 简化：到下周日
        days_to_sunday = 6 - week_start.weekday()
        week_end = week_start + timedelta(days=days_to_sunday)

        # 如果 week_end 超过 90 天范围，截断
        if week_end > end_date:
            week_end = end_date

        week_index += 1
        weeks.append({
            "week_index": week_index,
            "week_start": week_start,
            "week_end": week_end,
        })

        # 移动到下一周
        current_date = week_end + timedelta(days=1)

    return weeks
