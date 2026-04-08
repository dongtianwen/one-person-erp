"""v1.6 报价工具函数——编号生成、金额计算、预览、编辑/删除判断。"""
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    QUOTE_NO_PREFIX,
    QUOTE_DECIMAL_PLACES,
    QUOTE_ESTIMATE_MAX_DAYS,
    QUOTE_VALID_TRANSITIONS,
)
from app.models.quotation import Quotation, QuotationChange

logger = logging.getLogger("app.quote_utils")


def calculate_quote_amount(
    estimate_days: int,
    daily_rate: Decimal | None,
    direct_cost: Decimal | None,
    risk_buffer_rate: Decimal,
    discount_amount: Decimal,
    tax_rate: Decimal,
) -> dict[str, Decimal]:
    """报价金额计算——所有金额四舍五入到 2 位小数，不允许负数。

    规则：
    - labor_amount = estimate_days * daily_rate（daily_rate 为空时为 0）
    - base_amount = labor_amount + direct_cost
    - buffer_amount = round(base_amount * risk_buffer_rate, 2)
    - subtotal_amount = round(base_amount + buffer_amount, 2)
    - tax_amount = round(subtotal_amount * tax_rate, 2)
    - total_amount = round(subtotal_amount - discount_amount + tax_amount, 2)
    """
    labor_amount = round(
        Decimal(estimate_days) * (daily_rate or Decimal("0")),
        QUOTE_DECIMAL_PLACES,
    )
    base_amount = round(
        labor_amount + (direct_cost or Decimal("0")),
        QUOTE_DECIMAL_PLACES,
    )
    buffer_amount = round(base_amount * risk_buffer_rate, QUOTE_DECIMAL_PLACES)
    subtotal_amount = round(base_amount + buffer_amount, QUOTE_DECIMAL_PLACES)
    tax_amount = round(subtotal_amount * tax_rate, QUOTE_DECIMAL_PLACES)
    total_amount = round(
        subtotal_amount - discount_amount + tax_amount,
        QUOTE_DECIMAL_PLACES,
    )

    if total_amount < 0:
        raise ValueError("总价不得为负数")

    return {
        "labor_amount": labor_amount,
        "base_amount": base_amount,
        "buffer_amount": buffer_amount,
        "subtotal_amount": subtotal_amount,
        "tax_amount": tax_amount,
        "total_amount": total_amount,
    }


async def generate_quote_no(db: AsyncSession) -> str:
    """生成报价单编号：BJ-YYYYMMDD-序号（当日从 001 起）。

    必须在创建事务中执行，防止并发重复。
    """
    today = date.today()
    prefix = f"{QUOTE_NO_PREFIX}-{today.strftime('%Y%m%d')}"
    result = await db.execute(
        select(Quotation.quote_no)
        .where(Quotation.quote_no.like(f"{prefix}%"))
        .order_by(Quotation.quote_no.desc())
    )
    existing = result.scalars().first()
    if existing:
        seq = int(existing.split("-")[-1]) + 1
    else:
        seq = 1
    return f"{prefix}-{seq:03d}"


def build_quote_preview(payload: dict[str, Any]) -> dict[str, Decimal]:
    """根据输入返回报价预览——不保存数据库，仅用于报价草稿预览。"""
    return calculate_quote_amount(
        estimate_days=payload["estimate_days"],
        daily_rate=payload.get("daily_rate"),
        direct_cost=payload.get("direct_cost"),
        risk_buffer_rate=payload.get("risk_buffer_rate", Decimal("0")),
        discount_amount=payload.get("discount_amount", Decimal("0")),
        tax_rate=payload.get("tax_rate", Decimal("0")),
    )


def can_edit_quote(quote: Quotation) -> bool:
    """accepted 之后，仅允许修改 notes。其他状态返回 True。"""
    return quote.status not in ("accepted", "rejected", "expired", "cancelled")


def can_delete_quote(quote: Quotation) -> bool:
    """accepted / rejected / expired / cancelled 不可删除。"""
    return quote.status in ("draft",)


async def convert_quote_to_contract(
    db: AsyncSession,
    quote_id: int,
) -> Quotation:
    """报价单一键转合同——单事务完成。

    规则：
    - 仅 accepted 状态的报价单可转换
    - 一张报价单只能转换一次
    - 转换成功后创建合同草稿
    - 转换操作必须在同一事务中完成
    - 转换成功后生成报价转换日志
    """
    import json
    from fastapi import HTTPException
    from app.models.contract import Contract
    from app.crud.contract import contract as contract_crud

    q = await db.execute(select(Quotation).where(Quotation.id == quote_id))
    quote = q.scalar_one_or_none()
    if not quote:
        raise HTTPException(status_code=404, detail="报价单不存在")
    if quote.status != "accepted":
        raise HTTPException(status_code=400, detail="仅已接受的报价单可转为合同")
    if quote.converted_contract_id:
        raise HTTPException(status_code=400, detail="该报价单已转为合同")

    # 记录变更前快照
    before = {"status": quote.status, "converted_contract_id": None}

    # 生成合同编号
    contract_no = await contract_crud.generate_contract_no(db)

    # 创建合同草稿
    new_contract = Contract(
        contract_no=contract_no,
        customer_id=quote.customer_id,
        title=quote.title,
        amount=float(quote.total_amount) if quote.total_amount else 0,
        status="draft",
        terms=quote.requirement_summary,
        quotation_id=quote.id,
    )
    db.add(new_contract)
    await db.flush()

    # 更新报价单
    quote.converted_contract_id = new_contract.id
    db.add(quote)
    await db.flush()

    # 记录变更日志
    after = {"status": quote.status, "converted_contract_id": new_contract.id}
    change = QuotationChange(
        quotation_id=quote_id,
        change_type="converted",
        before_snapshot=json.dumps(before, ensure_ascii=False, default=str),
        after_snapshot=json.dumps(after, ensure_ascii=False, default=str),
        created_at=datetime.utcnow(),
    )
    db.add(change)

    await db.commit()
    await db.refresh(quote)
    await db.refresh(new_contract)

    logger.info(
        "报价转合同成功 | quote_id=%d contract_id=%d contract_no=%s",
        quote_id, new_contract.id, contract_no,
    )
    return quote
