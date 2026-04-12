"""v1.9 三表数据一致性校验——合同/收款/发票只读校验工具。"""

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import CONSISTENCY_CHECK_TOLERANCE
from app.core.logging import get_logger
from app.models.contract import Contract
from app.models.customer import Customer
from app.models.finance import FinanceRecord
from app.models.invoice import Invoice

logger = get_logger("consistency_utils")


async def get_contract_received_amount(
    db: AsyncSession, contract_id: int
) -> Decimal:
    """只读：获取合同实收总额（finance_records.amount 之和）。"""
    stmt = select(func.coalesce(func.sum(FinanceRecord.amount), 0)).where(
        FinanceRecord.contract_id == contract_id,
    )
    result = await db.execute(stmt)
    return Decimal(str(result.scalar()))


async def get_contract_invoiced_amount_active(
    db: AsyncSession, contract_id: int
) -> Decimal:
    """只读：获取合同已开票总额（排除 cancelled 状态）。"""
    stmt = select(func.coalesce(func.sum(Invoice.total_amount), 0)).where(
        Invoice.contract_id == contract_id,
        Invoice.status != "cancelled",
    )
    result = await db.execute(stmt)
    return Decimal(str(result.scalar()))


async def get_contract_verified_invoice_amount(
    db: AsyncSession, contract_id: int
) -> Decimal:
    """只读：获取合同 status='verified' 的发票总额。"""
    stmt = select(func.coalesce(func.sum(Invoice.total_amount), 0)).where(
        Invoice.contract_id == contract_id,
        Invoice.status == "verified",
    )
    result = await db.execute(stmt)
    return Decimal(str(result.scalar()))


def detect_payment_gap(
    contract_amount: Decimal, received_amount: Decimal
) -> dict | None:
    """检测未收款差异。差值 <= CONSISTENCY_CHECK_TOLERANCE 返回 None。"""
    gap = contract_amount - received_amount
    if gap > Decimal(str(CONSISTENCY_CHECK_TOLERANCE)):
        return {
            "issue_type": "payment_gap",
            "gap_amount": float(gap),
        }
    return None


def detect_invoice_payment_mismatch(
    verified_amount: Decimal, received_amount: Decimal
) -> dict | None:
    """检测核销发票与实收差异。差值 <= CONSISTENCY_CHECK_TOLERANCE 返回 None。"""
    diff = abs(verified_amount - received_amount)
    if diff > Decimal(str(CONSISTENCY_CHECK_TOLERANCE)):
        return {
            "issue_type": "invoice_payment_mismatch",
            "gap_amount": float(diff),
        }
    return None


def _build_issue(
    issue_type: str, contract_id: int, contract_no: str,
    customer_name: str, description: str, gap_amount: float,
    amounts: dict, **extra: Any,
) -> dict[str, Any]:
    """构建单条 issue 字典。"""
    return {
        "issue_type": issue_type,
        "contract_id": contract_id,
        "contract_no": contract_no,
        "customer_name": customer_name,
        "description": description,
        "gap_amount": gap_amount,
        **amounts,
        **extra,
    }


def _make_amounts(contract_amount, received_amount, invoiced_amount, verified_amount):
    """生成公共金额字段。"""
    return {
        "contract_amount": float(contract_amount),
        "received_amount": float(received_amount),
        "invoiced_amount": float(invoiced_amount),
        "verified_invoice_amount": float(verified_amount),
    }


async def _check_payment_gap(
    db: AsyncSession, contract_id: int, contract_no: str,
    customer_name: str, contract_amount: Decimal,
    received_amount: Decimal, amounts: dict,
) -> list[dict]:
    """维度1: 收款差异。"""
    issues = []
    pg = detect_payment_gap(contract_amount, received_amount)
    if pg:
        issues.append(_build_issue(
            pg["issue_type"], contract_id, contract_no, customer_name,
            f"合同金额 {float(contract_amount):.2f}，实收 {float(received_amount):.2f}，差额 {pg['gap_amount']:.2f}",
            pg["gap_amount"], amounts,
        ))
    return issues


async def _check_invoice_gap(
    db: AsyncSession, contract_id: int, contract_no: str,
    customer_name: str, contract_amount: Decimal,
    invoiced_amount: Decimal, amounts: dict,
) -> list[dict]:
    """维度2: 开票差异。"""
    issues = []
    invoice_gap = contract_amount - invoiced_amount
    if invoice_gap > Decimal(str(CONSISTENCY_CHECK_TOLERANCE)):
        issues.append(_build_issue(
            "invoice_gap", contract_id, contract_no, customer_name,
            f"合同金额 {float(contract_amount):.2f}，已开票 {float(invoiced_amount):.2f}，差额 {float(invoice_gap):.2f}",
            float(invoice_gap), amounts,
        ))
    return issues


async def _check_unlinked_payments(
    db: AsyncSession, contract_id: int, contract_no: str,
    customer_name: str, amounts: dict,
) -> list[dict]:
    """维度3: 未关联发票的收款。"""
    issues = []
    stmt_unlinked = select(FinanceRecord).where(
        FinanceRecord.contract_id == contract_id,
        FinanceRecord.invoice_id.is_(None),
    )
    result_unlinked = await db.execute(stmt_unlinked)
    unlinked_records = result_unlinked.scalars().all()
    if unlinked_records:
        total_unlinked = sum(Decimal(str(r.amount)) for r in unlinked_records)
        issues.append(_build_issue(
            "unlinked_payment", contract_id, contract_no, customer_name,
            f"有 {len(unlinked_records)} 笔收款未关联发票，合计 {float(total_unlinked):.2f}",
            float(total_unlinked), amounts, unlinked_count=len(unlinked_records),
        ))
    return issues


async def _check_mismatch(
    db: AsyncSession, contract_id: int, contract_no: str,
    customer_name: str, verified_amount: Decimal,
    received_amount: Decimal, amounts: dict,
) -> list[dict]:
    """维度4: 核销发票与实收差异。"""
    issues = []
    mismatch = detect_invoice_payment_mismatch(verified_amount, received_amount)
    if mismatch:
        issues.append(_build_issue(
            mismatch["issue_type"], contract_id, contract_no, customer_name,
            f"已核销发票 {float(verified_amount):.2f}，实收 {float(received_amount):.2f}，差异 {mismatch['gap_amount']:.2f}",
            mismatch["gap_amount"], amounts,
        ))
    return issues


async def check_contract_consistency(
    db: AsyncSession, contract_id: int
) -> list[dict[str, Any]]:
    """对单个合同做四维度只读校验，返回该合同的 issues 列表（空列表=无问题）。"""
    stmt = (
        select(Contract, Customer.name)
        .join(Customer, Contract.customer_id == Customer.id)
        .where(Contract.id == contract_id)
    )
    result = await db.execute(stmt)
    row = result.one_or_none()
    if row is None:
        return []

    contract, customer_name = row
    contract_amount = Decimal(str(contract.amount))
    contract_no = contract.contract_no

    received_amount = await get_contract_received_amount(db, contract_id)
    invoiced_amount = await get_contract_invoiced_amount_active(db, contract_id)
    verified_amount = await get_contract_verified_invoice_amount(db, contract_id)

    amounts = _make_amounts(contract_amount, received_amount, invoiced_amount, verified_amount)

    issues: list[dict] = []
    issues.extend(await _check_payment_gap(db, contract_id, contract_no, customer_name, contract_amount, received_amount, amounts))
    issues.extend(await _check_invoice_gap(db, contract_id, contract_no, customer_name, contract_amount, invoiced_amount, amounts))
    issues.extend(await _check_unlinked_payments(db, contract_id, contract_no, customer_name, amounts))
    issues.extend(await _check_mismatch(db, contract_id, contract_no, customer_name, verified_amount, received_amount, amounts))
    return issues


async def check_all_contracts_consistency(
    db: AsyncSession,
) -> dict[str, Any]:
    """对所有合同做只读校验，返回汇总报告。"""
    stmt = select(Contract.id)
    result = await db.execute(stmt)
    contract_ids = [row[0] for row in result.fetchall()]

    all_issues: list[dict[str, Any]] = []
    contracts_with_issues = 0

    for cid in contract_ids:
        try:
            issues = await check_contract_consistency(db, cid)
            if issues:
                contracts_with_issues += 1
                all_issues.extend(issues)
        except Exception as e:
            logger.error("一致性校验单合同失败 | contract_id=%d error=%s", cid, e)

    logger.info("一致性校验完成 | total=%d issues=%d", len(contract_ids), len(all_issues))
    return {
        "checked_at": datetime.utcnow().isoformat(),
        "summary": {
            "total_contracts_checked": len(contract_ids),
            "contracts_with_issues": contracts_with_issues,
            "total_issue_count": len(all_issues),
        },
        "issues": all_issues,
    }
