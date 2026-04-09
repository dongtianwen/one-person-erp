"""v1.8 发票台账异步工具函数——发票编号生成、金额计算、状态流转校验。"""

from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    INVOICE_NO_PREFIX,
    INVOICE_TAX_RATE_STANDARD,
    INVOICE_TAX_RATE_SMALL,
    INVOICE_STATUS_WHITELIST,
    INVOICE_VALID_TRANSITIONS,
)
from app.models.invoice import Invoice
from app.models.contract import Contract


async def generate_invoice_no(db: AsyncSession, invoice_date: Optional[date] = None) -> str:
    """
    生成发票编号，格式：INV-YYYYMMDD-序号（当日从 001 起）。

    使用异步查询保证并发安全，同一天内序号递增。

    Args:
        db: 异步数据库会话
        invoice_date: 发票日期，默认为今日

    Returns:
        发票编号，如 INV-20260409-001
    """
    if invoice_date is None:
        invoice_date = date.today()

    date_str = invoice_date.strftime("%Y%m%d")
    prefix = f"{INVOICE_NO_PREFIX}-{date_str}"

    # 查询当日最大序号
    result = await db.execute(
        select(Invoice.invoice_no)
        .where(Invoice.invoice_no.like(f"{prefix}-%"))
        .order_by(Invoice.invoice_no.desc())
        .limit(1)
    )
    last_no = result.scalar_one_or_none()

    if last_no:
        # 提取序号并递增
        last_seq = int(last_no.split("-")[-1])
        new_seq = last_seq + 1
    else:
        # 当日第一张发票
        new_seq = 1

    # 格式化序号为 3 位数字
    seq_str = f"{new_seq:03d}"
    invoice_no = f"{prefix}-{seq_str}"

    return invoice_no


def calculate_invoice_amount(
    amount_excluding_tax: Decimal, tax_rate: Optional[Decimal] = None
) -> dict:
    """
    计算发票税额和价税合计。

    tax_amount = round(amount_excluding_tax * tax_rate, 2)
    total_amount = round(amount_excluding_tax + tax_amount, 2)

    Args:
        amount_excluding_tax: 不含税金额
        tax_rate: 税率，默认使用标准税率 0.13

    Returns:
        {"tax_amount": Decimal, "total_amount": Decimal}

    Raises:
        ValueError: 金额为负数
    """
    amount = Decimal(str(amount_excluding_tax))
    if amount < 0:
        raise ValueError("不含税金额不得为负数")

    if tax_rate is None:
        tax_rate = Decimal(str(INVOICE_TAX_RATE_STANDARD))
    else:
        tax_rate = Decimal(str(tax_rate))

    # 计算税额，四舍五入到 2 位小数
    tax_amount = (amount * tax_rate).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    # 计算价税合计
    total_amount = (amount + tax_amount).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    return {
        "tax_amount": tax_amount,
        "total_amount": total_amount,
    }


async def get_contract_invoiced_amount(
    db: AsyncSession, contract_id: int, exclude_invoice_id: Optional[int] = None
) -> Decimal:
    """
    获取合同已开票总额（排除 cancelled 状态的发票）。

    Args:
        db: 异步数据库会话
        contract_id: 合同 ID
        exclude_invoice_id: 排除的发票 ID（用于更新场景）

    Returns:
        已开票总额
    """
    query = select(func.coalesce(func.sum(Invoice.total_amount), 0)).where(
        and_(
            Invoice.contract_id == contract_id,
            Invoice.status != "cancelled",
        )
    )

    if exclude_invoice_id:
        query = query.where(Invoice.id != exclude_invoice_id)

    result = await db.execute(query)
    return Decimal(str(result.scalar()))


async def validate_invoice_amount(
    db: AsyncSession,
    contract_id: int,
    new_amount: Decimal,
    exclude_invoice_id: Optional[int] = None,
) -> bool:
    """
    校验发票累计金额是否超合同金额。

    同一合同下 status != 'cancelled' 的发票 total_amount 之和不超合同金额。

    Args:
        db: 异步数据库会话
        contract_id: 合同 ID
        new_amount: 新增/修改的发票金额
        exclude_invoice_id: 排除的发票 ID（用于更新场景）

    Returns:
        True if 校验通过，False if 超限

    Raises:
        ValueError: 合同不存在
    """
    new_amount = Decimal(str(new_amount))
    if new_amount < 0:
        raise ValueError("发票金额不得为负数")

    # 获取合同金额
    result = await db.execute(
        select(Contract.amount).where(Contract.id == contract_id)
    )
    contract_amount = result.scalar_one_or_none()
    if contract_amount is None:
        raise ValueError(f"合同 ID {contract_id} 不存在")

    contract_amount = Decimal(str(contract_amount))

    # 获取已开票总额
    invoiced_amount = await get_contract_invoiced_amount(
        db, contract_id, exclude_invoice_id
    )

    # 校验
    return (invoiced_amount + new_amount) <= contract_amount


def validate_invoice_transition(current: str, target: str) -> bool:
    """
    校验发票状态流转是否合法。

    状态流转规则：
    - draft → issued / received / verified / cancelled
    - issued → received / verified / cancelled
    - received → verified / cancelled
    - verified / cancelled 为终态，不可再流转

    Args:
        current: 当前状态
        target: 目标状态

    Returns:
        True if 流转合法，False otherwise

    Raises:
        ValueError: 状态不在白名单中
    """
    if current not in INVOICE_STATUS_WHITELIST:
        raise ValueError(f"当前状态 '{current}' 不在白名单中")
    if target not in INVOICE_STATUS_WHITELIST:
        raise ValueError(f"目标状态 '{target}' 不在白名单中")

    valid_targets = INVOICE_VALID_TRANSITIONS.get(current, [])
    return target in valid_targets


async def get_invoice_summary(
    db: AsyncSession,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> dict:
    """
    按状态统计发票数量和金额。

    Args:
        db: 异步数据库会话
        start_date: 起始日期（可选）
        end_date: 结束日期（可选）

    Returns:
        {
            "draft": {"count": int, "total_amount": Decimal},
            "issued": {"count": int, "total_amount": Decimal},
            ...
        }
    """
    query = select(
        Invoice.status,
        func.count(Invoice.id).label("count"),
        func.coalesce(func.sum(Invoice.total_amount), 0).label("total"),
    )

    conditions = []
    if start_date and end_date:
        conditions.append(
            and_(Invoice.invoice_date >= start_date, Invoice.invoice_date <= end_date)
        )
    elif start_date:
        conditions.append(Invoice.invoice_date >= start_date)
    elif end_date:
        conditions.append(Invoice.invoice_date <= end_date)

    if conditions:
        query = query.where(and_(*conditions))

    query = query.group_by(Invoice.status)
    result = await db.execute(query)

    summary = {}
    for status in INVOICE_STATUS_WHITELIST:
        summary[status] = {"count": 0, "total_amount": Decimal("0.00")}

    for row in result:
        status_name, count, total = row.status, row.count, row.total
        summary[status_name] = {
            "count": count,
            "total_amount": Decimal(str(total)),
        }

    return summary


def calculate_accounting_period(transaction_date: date) -> str:
    """
    计算会计期间。

    会计期间按自然月界定：YYYY-MM

    Args:
        transaction_date: 交易日期

    Returns:
        会计期间字符串，如 "2024-01"

    Raises:
        ValueError: 日期无效
    """
    if not isinstance(transaction_date, date):
        transaction_date = datetime.strptime(str(transaction_date), "%Y-%m-%d").date()

    return transaction_date.strftime("%Y-%m")
