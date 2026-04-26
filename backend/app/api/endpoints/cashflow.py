"""FR-301 现金流预测 API。"""

import logging
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.logging import get_logger

logger = get_logger("cashflow")
from app.api.deps import get_current_user
from app.models.user import User
from app.models.contract import Contract
from app.models.finance import FinanceRecord
from app.core.constants import (
    CASHFLOW_FORECAST_DAYS,
    CASHFLOW_WEEKS_PER_MONTH,
    CASHFLOW_HISTORY_MONTHS,
    CASHFLOW_CONTRACT_STATUSES,
    DECIMAL_PLACES,
    WEEK_START_DAY,
)
from app.core.cashflow_utils import get_forecast_weeks

router = APIRouter()


def _round2(value) -> float:
    """四舍五入到 2 位小数。"""
    return round(float(value), DECIMAL_PLACES)


async def _calculate_weekly_income(
    weeks: list[dict], db: AsyncSession
) -> dict[int, float]:
    """
    按 expected_payment_date 将应收账款分配到对应周。
    - 只处理 contracts.status IN CASHFLOW_CONTRACT_STATUSES 的合同
    - expected_payment_date 为 NULL 的合同跳过
    - 应收账款 <= 0 的合同跳过
    """
    result: dict[int, float] = {}

    # 查询符合条件的合同
    contracts_result = await db.execute(
        select(Contract).where(
            Contract.status.in_(CASHFLOW_CONTRACT_STATUSES),
            Contract.is_deleted == False,
            Contract.expected_payment_date.isnot(None),
        )
    )
    contracts = contracts_result.scalars().all()

    for contract in contracts:
        # 计算已确认收入
        income_result = await db.execute(
            select(func.coalesce(func.sum(FinanceRecord.amount), 0)).where(
                FinanceRecord.type == "income",
                FinanceRecord.status == "confirmed",
                FinanceRecord.contract_id == contract.id,
                FinanceRecord.is_deleted == False,
            )
        )
        confirmed_income = float(income_result.scalar() or 0)

        # 应收账款 = 合同金额 - 已确认收入
        receivable = float(contract.amount) - confirmed_income
        if receivable <= 0:
            continue

        # 找到对应的周
        pay_date = contract.expected_payment_date
        for week in weeks:
            if week["week_start"] <= pay_date <= week["week_end"]:
                idx = week["week_index"]
                result[idx] = result.get(idx, 0) + receivable
                break

    return result


async def _calculate_weekly_expense(
    weeks: list[dict], db: AsyncSession, start_date: date
) -> dict[int, float]:
    """
    基于历史支出 + 未来里程碑付款计算周支出预测。
    - 基础支出：最近 3 个完整自然月的周均支出
    - 里程碑支出：按 payment_due_date 分配到对应周
    """
    from app.models.project import Milestone

    today = start_date
    month = today.month
    year = today.year

    end_month = month - 1
    end_year = year
    if end_month == 0:
        end_month = 12
        end_year = year - 1

    start_month = end_month - 2
    start_year = end_year
    if start_month <= 0:
        start_month += 12
        start_year -= 1

    from datetime import date as date_type
    hist_start = date_type(start_year, start_month, 1)
    if end_month == 12:
        hist_end = date_type(end_year + 1, 1, 1) - timedelta(days=1)
    else:
        hist_end = date_type(end_year, end_month + 1, 1) - timedelta(days=1)

    expense_result = await db.execute(
        select(func.coalesce(func.sum(FinanceRecord.amount), 0)).where(
            FinanceRecord.type == "expense",
            FinanceRecord.status.in_(["confirmed", "paid"]),
            FinanceRecord.date >= hist_start,
            FinanceRecord.date <= hist_end,
            FinanceRecord.is_deleted == False,
        )
    )
    total_expense = float(expense_result.scalar() or 0)

    if total_expense == 0:
        weekly_base = 0.0
    else:
        monthly_avg = total_expense / CASHFLOW_HISTORY_MONTHS
        weekly_base = _round2(monthly_avg / CASHFLOW_WEEKS_PER_MONTH)

    result = {w["week_index"]: weekly_base for w in weeks}

    forecast_end = today + timedelta(days=CASHFLOW_FORECAST_DAYS - 1)
    milestone_result = await db.execute(
        select(Milestone).where(
            Milestone.is_deleted == False,
            Milestone.payment_status.in_(["pending", "unpaid"]),
            Milestone.payment_due_date.isnot(None),
            Milestone.payment_amount > 0,
        )
    )
    milestones = milestone_result.scalars().all()

    for ms in milestones:
        due = ms.payment_due_date
        if hasattr(due, "date"):
            due = due.date()
        if due < today or due > forecast_end:
            continue

        for week in weeks:
            ws = week["week_start"]
            we = week["week_end"]
            if hasattr(ws, "date"):
                ws = ws.date()
            if hasattr(we, "date"):
                we = we.date()
            if ws <= due <= we:
                idx = week["week_index"]
                result[idx] = result.get(idx, 0) + float(ms.payment_amount)
                break

    return result


@router.get("/forecast")
async def get_cashflow_forecast(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """GET /api/v1/cashflow/forecast — 90 天现金流预测"""
    start_date = date.today()
    weeks = get_forecast_weeks(start_date)

    # 计算周收入和周支出
    weekly_income = await _calculate_weekly_income(weeks, db)
    weekly_expense = await _calculate_weekly_expense(weeks, db, start_date)

    # 组装预测数据
    forecast = []
    total_income = 0.0
    total_expense = 0.0
    total_net = 0.0
    net_30d = 0.0
    days_covered = 0

    for week in weeks:
        idx = week["week_index"]
        income = _round2(weekly_income.get(idx, 0))
        expense = _round2(weekly_expense.get(idx, 0))
        net = _round2(income - expense)
        week_days = (week["week_end"] - week["week_start"]).days + 1

        forecast.append({
            "week_index": idx,
            "week_start": week["week_start"].isoformat(),
            "week_end": week["week_end"].isoformat(),
            "predicted_income": income,
            "predicted_expense": expense,
            "predicted_net": net,
        })

        total_income += income
        total_expense += expense
        total_net += net

        # 前 30 天净现金流累计
        if days_covered < 30:
            net_30d += net
            days_covered += week_days

    logger.info("cashflow_forecast | weeks=%d income=%.2f expense=%.2f net=%.2f net_30d=%.2f", len(forecast), total_income, total_expense, total_net, net_30d)
    return {
        "forecast": forecast,
        "summary": {
            "total_predicted_income": _round2(total_income),
            "total_predicted_expense": _round2(total_expense),
            "total_predicted_net": _round2(total_net),
            "net_30d": _round2(net_30d),
        },
    }
