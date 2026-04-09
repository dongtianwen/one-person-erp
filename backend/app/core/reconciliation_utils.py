"""v1.8 会计期间对账工具函数——期间汇总、客户分解、未对账记录识别。"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select, func, and_, case, literal_column
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.constants import ACCOUNTING_PERIOD_FORMAT
from app.core.export_utils import get_period_date_range
from app.core.logging import get_logger
from app.models.contract import Contract
from app.models.customer import Customer
from app.models.finance import FinanceRecord
from app.models.invoice import Invoice

logger = get_logger("reconciliation_utils")


async def get_opening_balance(
    db: AsyncSession,
    accounting_period: str,
) -> dict[str, float]:
    """计算期初余额（第一期返回全零）。

    期初余额 = 上期期末余额
    若为系统内第一期，则期初全零

    Args:
        db: 数据库会话
        accounting_period: 会计期间 YYYY-MM

    Returns:
        {"accounts_receivable": float, "unbilled_amount": float, "total": float}
    """
    # 计算上一个期间的结束日期
    year, month = map(int, accounting_period.split("-"))

    # 上个月的最后一天即本期期初
    if month == 1:
        # 1月的第一天是 1月1日，期初为0
        return {
            "accounts_receivable": 0.0,
            "unbilled_amount": 0.0,
            "total": 0.0,
        }

    # 计算上个月的最后一天
    if month == 1:
        prev_month = 12
        prev_year = year - 1
    else:
        prev_month = month - 1
        prev_year = year

    # 上个月的最后一天
    if prev_month == 12:
        prev_period_end = date(prev_year + 1, 1, 1) - __import__('datetime').timedelta(days=1)
    else:
        prev_period_end = date(prev_year, prev_month + 1, 1) - __import__('datetime').timedelta(days=1)

    # 获取上期期末余额（截止到上月底的所有合同金额 - 收款金额）
    # 累计合同金额（所有签订的合同）
    stmt_contracts = (
        select(func.sum(Contract.amount))
        .where(Contract.signed_date <= prev_period_end)
    )
    result_contracts = await db.execute(stmt_contracts)
    total_contracts = result_contracts.scalar() or 0

    # 累计开票金额（所有已开具的发票，不包括 cancelled）
    stmt_invoices = (
        select(func.sum(Invoice.total_amount))
        .where(
            Invoice.invoice_date <= prev_period_end,
            Invoice.status != "cancelled",
        )
    )
    result_invoices = await db.execute(stmt_invoices)
    total_invoices = result_invoices.scalar() or 0

    # 累计收款金额
    stmt_payments = (
        select(func.sum(FinanceRecord.amount))
        .where(
            FinanceRecord.date <= prev_period_end,
            FinanceRecord.type == "income",
        )
    )
    result_payments = await db.execute(stmt_payments)
    total_payments = result_payments.scalar() or 0

    # 期初应收账款 = 累计合同 - 累计收款
    accounts_receivable = float(total_contracts) - float(total_payments)

    # 未开票金额 = 累计合同 - 累计开票
    unbilled_amount = float(total_contracts) - float(total_invoices)

    return {
        "accounts_receivable": max(0, accounts_receivable),
        "unbilled_amount": max(0, unbilled_amount),
        "total": max(0, accounts_receivable) + max(0, unbilled_amount),
    }


async def get_current_period_activity(
    db: AsyncSession,
    accounting_period: str,
) -> dict[str, Any]:
    """统计本期活动数据。

    Args:
        db: 数据库会话
        accounting_period: 会计期间 YYYY-MM

    Returns:
        {
            "contracts_signed": int,
            "contracts_amount": float,
            "invoices_issued": int,
            "invoices_amount": float,
            "payments_received": int,
            "payments_amount": float,
            "invoices_verified": int,
            "verified_amount": float,
        }
    """
    period_start, period_end = get_period_date_range(accounting_period)

    # 本期签订合同
    stmt_contracts = (
        select(
            func.count(Contract.id).label("count"),
            func.sum(Contract.amount).label("amount"),
        )
        .where(
            Contract.signed_date >= period_start,
            Contract.signed_date <= period_end,
        )
    )
    result_contracts = await db.execute(stmt_contracts)
    row_contracts = result_contracts.one_or_none()

    # 本期开具发票（不包括 cancelled）
    stmt_invoices = (
        select(
            func.count(Invoice.id).label("count"),
            func.sum(Invoice.total_amount).label("amount"),
        )
        .where(
            Invoice.invoice_date >= period_start,
            Invoice.invoice_date <= period_end,
            Invoice.status != "cancelled",
        )
    )
    result_invoices = await db.execute(stmt_invoices)
    row_invoices = result_invoices.one_or_none()

    # 本期收款
    stmt_payments = (
        select(
            func.count(FinanceRecord.id).label("count"),
            func.sum(FinanceRecord.amount).label("amount"),
        )
        .where(
            FinanceRecord.date >= period_start,
            FinanceRecord.date <= period_end,
            FinanceRecord.type == "income",
        )
    )
    result_payments = await db.execute(stmt_payments)
    row_payments = result_payments.one_or_none()

    # 本期核销发票
    stmt_verified = (
        select(
            func.count(Invoice.id).label("count"),
            func.sum(Invoice.total_amount).label("amount"),
        )
        .where(
            Invoice.verified_at >= period_start,
            Invoice.verified_at <= period_end,
            Invoice.status == "verified",
        )
    )
    result_verified = await db.execute(stmt_verified)
    row_verified = result_verified.one_or_none()

    def safe_int(val):
        return int(val) if val is not None else 0

    def safe_float(val):
        return float(val) if val is not None else 0.0

    return {
        "contracts_signed": safe_int(row_contracts[0]) if row_contracts else 0,
        "contracts_amount": safe_float(row_contracts[1]) if row_contracts else 0.0,
        "invoices_issued": safe_int(row_invoices[0]) if row_invoices else 0,
        "invoices_amount": safe_float(row_invoices[1]) if row_invoices else 0.0,
        "payments_received": safe_int(row_payments[0]) if row_payments else 0,
        "payments_amount": safe_float(row_payments[1]) if row_payments else 0.0,
        "invoices_verified": safe_int(row_verified[0]) if row_verified else 0,
        "verified_amount": safe_float(row_verified[1]) if row_verified else 0.0,
    }


async def get_closing_balance(
    db: AsyncSession,
    accounting_period: str,
) -> dict[str, float]:
    """计算期末余额。

    期末应收账款 = 期初应收账款 + 本期合同 - 本期收款
    未开票金额 = 期初未开票 + 本期合同 - 本期开票

    Args:
        db: 数据库会话
        accounting_period: 会计期间 YYYY-MM

    Returns:
        {"accounts_receivable": float, "unbilled_amount": float, "total": float}
    """
    period_start, period_end = get_period_date_range(accounting_period)

    # 获取期初余额
    opening = await get_opening_balance(db, accounting_period)

    # 本期签订合同金额
    stmt_contracts = (
        select(func.sum(Contract.amount))
        .where(
            Contract.signed_date >= period_start,
            Contract.signed_date <= period_end,
        )
    )
    result_contracts = await db.execute(stmt_contracts)
    contracts_amount = result_contracts.scalar() or 0

    # 本期开票金额
    stmt_invoices = (
        select(func.sum(Invoice.total_amount))
        .where(
            Invoice.invoice_date >= period_start,
            Invoice.invoice_date <= period_end,
            Invoice.status != "cancelled",
        )
    )
    result_invoices = await db.execute(stmt_invoices)
    invoices_amount = result_invoices.scalar() or 0

    # 本期收款金额
    stmt_payments = (
        select(func.sum(FinanceRecord.amount))
        .where(
            FinanceRecord.date >= period_start,
            FinanceRecord.date <= period_end,
            FinanceRecord.type == "income",
        )
    )
    result_payments = await db.execute(stmt_payments)
    payments_amount = result_payments.scalar() or 0

    # 期末应收账款 = 期初 + 本期合同 - 本期收款
    accounts_receivable = opening["accounts_receivable"] + float(contracts_amount) - float(payments_amount)

    # 未开票金额 = 期初未开票 + 本期合同 - 本期开票
    unbilled_amount = opening["unbilled_amount"] + float(contracts_amount) - float(invoices_amount)

    return {
        "accounts_receivable": max(0, accounts_receivable),
        "unbilled_amount": max(0, unbilled_amount),
        "total": max(0, accounts_receivable) + max(0, unbilled_amount),
    }


async def get_customer_breakdown(
    db: AsyncSession,
    accounting_period: str,
) -> list[dict[str, Any]]:
    """按客户分解本期活动。

    Args:
        db: 数据库会话
        accounting_period: 会计期间 YYYY-MM

    Returns:
        [
            {
                "customer_id": int,
                "customer_name": str,
                "contracts_amount_this_period": float,
                "invoices_amount_this_period": float,
                "payments_amount_this_period": float,
                "outstanding_balance": float,
            },
            ...
        ]
    """
    period_start, period_end = get_period_date_range(accounting_period)

    # 获取本期有活动的客户（有合同、开票或收款）
    stmt_customers = (
        select(Customer.id, Customer.name)
        .join(Contract, Customer.id == Contract.customer_id)
        .where(
            Contract.signed_date >= period_start,
            Contract.signed_date <= period_end,
        )
        .distinct()
    )
    result_customers = await db.execute(stmt_customers)
    customers = result_customers.fetchall()

    breakdown = []
    for customer_id, customer_name in customers:
        # 本期合同金额
        stmt_contracts = (
            select(func.sum(Contract.amount))
            .where(
                Contract.customer_id == customer_id,
                Contract.signed_date >= period_start,
                Contract.signed_date <= period_end,
            )
        )
        result_contracts = await db.execute(stmt_contracts)
        contracts_amount = float(result_contracts.scalar() or 0)

        # 本期开票金额
        stmt_invoices = (
            select(func.sum(Invoice.total_amount))
            .join(Contract, Invoice.contract_id == Contract.id)
            .where(
                Contract.customer_id == customer_id,
                Invoice.invoice_date >= period_start,
                Invoice.invoice_date <= period_end,
                Invoice.status != "cancelled",
            )
        )
        result_invoices = await db.execute(stmt_invoices)
        invoices_amount = float(result_invoices.scalar() or 0)

        # 本期收款金额
        stmt_payments = (
            select(func.sum(FinanceRecord.amount))
            .join(Contract, FinanceRecord.contract_id == Contract.id)
            .where(
                Contract.customer_id == customer_id,
                FinanceRecord.date >= period_start,
                FinanceRecord.date <= period_end,
                FinanceRecord.type == "income",
            )
        )
        result_payments = await db.execute(stmt_payments)
        payments_amount = float(result_payments.scalar() or 0)

        # 计算未结余额 = 本期合同 - 本期收款
        outstanding_balance = contracts_amount - payments_amount

        breakdown.append({
            "customer_id": customer_id,
            "customer_name": customer_name,
            "contracts_amount_this_period": contracts_amount,
            "invoices_amount_this_period": invoices_amount,
            "payments_amount_this_period": payments_amount,
            "outstanding_balance": outstanding_balance,
        })

    return breakdown


async def get_unreconciled_records(
    db: AsyncSession,
    accounting_period: str,
) -> list[dict[str, Any]]:
    """获取未对账记录（无关联合同的收款记录）。

    Args:
        db: 数据库会话
        accounting_period: 会计期间 YYYY-MM

    Returns:
        [
            {
                "record_id": int,
                "record_type": str,
                "amount": float,
                "transaction_date": date,
                "reason": str,
            },
            ...
        ]
    """
    period_start, period_end = get_period_date_range(accounting_period)

    # 获取本期无关联合同的收款记录
    stmt = (
        select(
            FinanceRecord.id,
            FinanceRecord.amount,
            FinanceRecord.date,
            FinanceRecord.description,
        )
        .where(
            FinanceRecord.contract_id.is_(None),
            FinanceRecord.date >= period_start,
            FinanceRecord.date <= period_end,
            FinanceRecord.type == "income",
        )
        .order_by(FinanceRecord.date.desc())
    )

    result = await db.execute(stmt)
    rows = result.fetchall()

    unreconciled = []
    for row in rows:
        unreconciled.append({
            "record_id": row.id,
            "record_type": "payment",
            "amount": float(row.amount),
            "transaction_date": row.date.isoformat(),
            "reason": "无匹配合同",
        })

    return unreconciled


async def generate_reconciliation_report(
    db: AsyncSession,
    accounting_period: str,
) -> dict[str, Any]:
    """生成完整对账报表。

    Args:
        db: 数据库会话
        accounting_period: 会计期间 YYYY-MM

    Returns:
        完整对账报表字典
    """
    period_start, period_end = get_period_date_range(accounting_period)

    opening = await get_opening_balance(db, accounting_period)
    current = await get_current_period_activity(db, accounting_period)
    closing = await get_closing_balance(db, accounting_period)
    breakdown = await get_customer_breakdown(db, accounting_period)
    unreconciled = await get_unreconciled_records(db, accounting_period)

    return {
        "accounting_period": accounting_period,
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "opening_balance": opening,
        "current_period": current,
        "closing_balance": closing,
        "breakdown": breakdown,
        "unreconciled_records": unreconciled,
    }


async def get_available_periods(db: AsyncSession) -> list[str]:
    """获取所有有数据的会计期间列表。

    Returns:
        ["2024-01", "2024-02", ...]
    """
    periods = set()

    # 从合同签订日期获取期间
    stmt_contracts = select(Contract.signed_date).where(Contract.signed_date.is_not(None))
    result_contracts = await db.execute(stmt_contracts)
    for row in result_contracts.fetchall():
        if row[0]:
            periods.add(row[0].strftime(ACCOUNTING_PERIOD_FORMAT))

    # 从收款日期获取期间
    stmt_payments = select(FinanceRecord.date).where(FinanceRecord.type == "income")
    result_payments = await db.execute(stmt_payments)
    for row in result_payments.fetchall():
        if row[0]:
            periods.add(row[0].strftime(ACCOUNTING_PERIOD_FORMAT))

    # 从开票日期获取期间
    stmt_invoices = select(Invoice.invoice_date).where(Invoice.status != "cancelled")
    result_invoices = await db.execute(stmt_invoices)
    for row in result_invoices.fetchall():
        if row[0]:
            periods.add(row[0].strftime(ACCOUNTING_PERIOD_FORMAT))

    return sorted(list(periods))


async def sync_reconciliation_status(
    db: AsyncSession,
    record_ids: list[int],
) -> int:
    """同步对账状态，原子事务。

    规则：
    - 有关联合同且合同有对应发票 → matched
    - 有关联发票且发票状态为 verified → verified
    - 其他 → pending

    Args:
        db: 数据库会话
        record_ids: 收款记录 ID 列表

    Returns:
        更新的记录数
    """
    updated_count = 0

    for record_id in record_ids:
        stmt = select(FinanceRecord).where(FinanceRecord.id == record_id)
        result = await db.execute(stmt)
        record = result.scalar_one_or_none()

        if not record:
            continue

        # 如果记录已关联发票
        if record.invoice_id:
            stmt_invoice = select(Invoice).where(Invoice.id == record.invoice_id)
            result_invoice = await db.execute(stmt_invoice)
            invoice = result_invoice.scalar_one_or_none()

            if invoice and invoice.status == "verified":
                # 发票已核销
                record.reconciliation_status = "verified"
            else:
                record.reconciliation_status = "matched"
        elif record.contract_id:
            # 有关联合同但无发票
            record.reconciliation_status = "matched"
        else:
            # 无关联
            record.reconciliation_status = "pending"

        updated_count += 1

    await db.commit()
    logger.info(f"对账状态同步完成，更新 {updated_count} 条记录")

    return updated_count
