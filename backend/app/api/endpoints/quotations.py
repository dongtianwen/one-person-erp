import logging
from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.quotation import Quotation, QuotationItem, QuotationChange
from app.models.contract import Contract
from app.crud.quotation import quotation as quotation_crud
from app.crud.contract import contract as contract_crud
from app.crud.customer import customer as customer_crud
from app.schemas.quotation import (
    QuotationCreate, QuotationUpdate, QuotationResponse, QuotationListResponse,
    QuotationPreviewRequest, QuotationPreviewResponse,
    QuotationItemCreate, QuotationItemResponse,
)
from app.core.constants import (
    QUOTE_NO_PREFIX, QUOTE_VALID_DAYS_DEFAULT, QUOTE_DECIMAL_PLACES,
    QUOTE_ESTIMATE_MAX_DAYS, QUOTE_VALID_TRANSITIONS,
)

logger = logging.getLogger("app.quotations")
router = APIRouter()


def _calculate_quote_amount(
    estimate_days: int,
    daily_rate: Decimal | None,
    direct_cost: Decimal | None,
    risk_buffer_rate: Decimal,
    discount_amount: Decimal,
    tax_rate: Decimal,
) -> dict:
    """报价金额计算——所有金额四舍五入到 2 位小数，不允许负数。"""
    labor_amount = round(Decimal(estimate_days) * (daily_rate or Decimal("0")), QUOTE_DECIMAL_PLACES)
    base_amount = round(labor_amount + (direct_cost or Decimal("0")), QUOTE_DECIMAL_PLACES)
    buffer_amount = round(base_amount * risk_buffer_rate, QUOTE_DECIMAL_PLACES)
    subtotal_amount = round(base_amount + buffer_amount, QUOTE_DECIMAL_PLACES)
    tax_amount = round(subtotal_amount * tax_rate, QUOTE_DECIMAL_PLACES)
    total_amount = round(subtotal_amount - discount_amount + tax_amount, QUOTE_DECIMAL_PLACES)

    # 所有金额不得为负数
    if total_amount < 0:
        raise HTTPException(status_code=422, detail="总价不得为负数")

    return {
        "labor_amount": labor_amount,
        "base_amount": base_amount,
        "buffer_amount": buffer_amount,
        "subtotal_amount": subtotal_amount,
        "tax_amount": tax_amount,
        "total_amount": total_amount,
    }


def _can_edit(quote: Quotation) -> bool:
    """accepted 之后仅允许修改 notes。"""
    return quote.status not in ("accepted", "rejected", "expired", "cancelled")


def _can_delete(quote: Quotation) -> bool:
    """accepted/rejected/expired/cancelled 不可删除。"""
    return quote.status in ("draft",)


def _trigger_requirement_freeze(project_id: int) -> None:
    """v1.7: 触发项目需求冻结。

    当报价单被接受时，自动冻结该项目需求。
    注意：此函数仅记录日志，实际冻结逻辑由 is_project_requirements_frozen_sync 判断。
    """
    logger = logging.getLogger("app.quotations")
    logger.info(f"报价单已接受，项目 {project_id} 需求已冻结")
    # 实际的冻结判断通过查询 quotation.status = 'accepted' 来实现
    # 这里只需要记录日志，不需要额外的数据库操作


def _validate_core_fields(updates: dict) -> None:
    """校验核心字段。"""
    if "estimate_days" in updates:
        if updates["estimate_days"] <= 0:
            raise HTTPException(status_code=422, detail="预计工期必须大于 0")
        if updates["estimate_days"] > QUOTE_ESTIMATE_MAX_DAYS:
            raise HTTPException(status_code=422, detail=f"预计工期不得超过 {QUOTE_ESTIMATE_MAX_DAYS} 天")

    for field_name in ("daily_rate", "direct_cost", "discount_amount", "tax_rate", "risk_buffer_rate"):
        if field_name in updates and updates[field_name] is not None:
            if Decimal(str(updates[field_name])) < 0:
                raise HTTPException(status_code=422, detail=f"{field_name} 不允许为负数")


async def _record_change(
    db: AsyncSession, quote_id: int, change_type: str, before: dict, after: dict,
) -> None:
    """记录报价变更日志。"""
    import json
    change = QuotationChange(
        quotation_id=quote_id,
        change_type=change_type,
        before_snapshot=json.dumps(before, ensure_ascii=False, default=str),
        after_snapshot=json.dumps(after, ensure_ascii=False, default=str),
        created_at=datetime.utcnow(),
    )
    db.add(change)


def _validate_update_permission(q: Quotation, update_data: dict) -> None:
    """校验更新权限：状态流转、编辑权限、accepted 限制。"""
    if "status" in update_data and update_data["status"] != q.status:
        new_status = update_data["status"]
        allowed = QUOTE_VALID_TRANSITIONS.get(q.status, [])
        if new_status not in allowed:
            raise HTTPException(
                status_code=422,
                detail=f"报价单状态不能从 '{q.status}' 变更为 '{new_status}'",
            )
    elif not _can_edit(q) and q.status != "accepted":
        raise HTTPException(status_code=400, detail="当前状态不允许编辑")

    if q.status == "accepted":
        if any(k != "notes" for k in update_data.keys()):
            raise HTTPException(status_code=400, detail="已接受的报价单仅允许修改备注")


def _recalc_amounts(q: Quotation, update_data: dict) -> set:
    """若金额相关字段变化则重新计算，返回已更新的金额字段集合。"""
    amount_keys = set()
    if not any(k in update_data for k in (
        "estimate_days", "daily_rate", "direct_cost",
        "risk_buffer_rate", "discount_amount", "tax_rate"
    )):
        return amount_keys

    amounts = _calculate_quote_amount(
        estimate_days=update_data.get("estimate_days", q.estimate_days),
        daily_rate=Decimal(str(update_data["daily_rate"])) if "daily_rate" in update_data and update_data["daily_rate"] is not None else q.daily_rate,
        direct_cost=Decimal(str(update_data["direct_cost"])) if "direct_cost" in update_data and update_data["direct_cost"] is not None else q.direct_cost,
        risk_buffer_rate=Decimal(str(update_data["risk_buffer_rate"])) if "risk_buffer_rate" in update_data else q.risk_buffer_rate,
        discount_amount=Decimal(str(update_data["discount_amount"])) if "discount_amount" in update_data else q.discount_amount,
        tax_rate=Decimal(str(update_data["tax_rate"])) if "tax_rate" in update_data else q.tax_rate,
    )
    for key in ("subtotal_amount", "tax_amount", "total_amount"):
        setattr(q, key, amounts[key])
        amount_keys.add(key)
    return amount_keys


def _apply_status_change(q: Quotation, update_data: dict) -> None:
    """处理状态变更，写入对应时间戳。

    v1.7: 当状态变更为 accepted 时，触发项目需求冻结。
    """
    if "status" not in update_data or update_data["status"] == q.status:
        return
    new_status = update_data["status"]
    q.status = new_status
    ts_field = {"sent": "sent_at", "accepted": "accepted_at", "rejected": "rejected_at"}.get(new_status)
    if ts_field:
        setattr(q, ts_field, datetime.utcnow())

    # v1.7: 报价 accepted 后触发需求冻结
    if new_status == "accepted" and q.project_id:
        _trigger_requirement_freeze(q.project_id)


@router.get("", response_model=QuotationListResponse)
async def list_quotations(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    customer_id: Optional[int] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    filters = {}
    if status:
        filters["status"] = status
    if customer_id:
        filters["customer_id"] = customer_id
    items, total = await quotation_crud.list(db, skip=skip, limit=limit, filters=filters, search=search)
    return QuotationListResponse(
        items=[QuotationResponse.model_validate(q) for q in items],
        total=total,
        page=(skip // limit) + 1,
        page_size=limit,
    )


@router.get("/{quote_id}", response_model=QuotationResponse)
async def get_quotation(
    quote_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = await quotation_crud.get(db, quote_id)
    if not q:
        raise HTTPException(status_code=404, detail="报价单不存在")
    return QuotationResponse.model_validate(q)


@router.post("", response_model=QuotationResponse, status_code=201)
async def create_quotation(
    quotation_in: QuotationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 校验客户存在
    customer = await customer_crud.get(db, quotation_in.customer_id)
    if not customer:
        raise HTTPException(status_code=400, detail="客户不存在")

    # 校验
    _validate_core_fields(quotation_in.model_dump())

    # 计算金额
    amounts = _calculate_quote_amount(
        estimate_days=quotation_in.estimate_days,
        daily_rate=quotation_in.daily_rate,
        direct_cost=quotation_in.direct_cost,
        risk_buffer_rate=quotation_in.risk_buffer_rate,
        discount_amount=quotation_in.discount_amount,
        tax_rate=quotation_in.tax_rate,
    )

    # 生成编号
    quote_no = await quotation_crud.generate_quote_no(db)

    # 创建——只取模型存在的金额字段
    obj_dict = quotation_in.model_dump()
    obj_dict["quote_no"] = quote_no
    for key in ("subtotal_amount", "tax_amount", "total_amount"):
        obj_dict[key] = amounts[key]
    db_obj = Quotation(**obj_dict)
    db.add(db_obj)

    try:
        await db.commit()
        await db.refresh(db_obj)
    except Exception as e:
        await db.rollback()
        logger.error("报价单创建失败 | error=%s", str(e))
        raise HTTPException(status_code=500, detail="报价单创建失败")

    return QuotationResponse.model_validate(db_obj)


@router.put("/{quote_id}", response_model=QuotationResponse)
async def update_quotation(
    quote_id: int,
    quotation_in: QuotationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = await quotation_crud.get(db, quote_id)
    if not q:
        raise HTTPException(status_code=404, detail="报价单不存在")

    update_data = quotation_in.model_dump(exclude_unset=True)
    _validate_update_permission(q, update_data)
    _validate_core_fields(update_data)

    before = {
        "title": q.title, "estimate_days": q.estimate_days,
        "daily_rate": str(q.daily_rate) if q.daily_rate else None,
        "total_amount": str(q.total_amount), "status": q.status,
    }

    amount_keys = _recalc_amounts(q, update_data)

    for field, val in update_data.items():
        if field != "status" and hasattr(q, field) and field not in amount_keys:
            setattr(q, field, val)

    _apply_status_change(q, update_data)
    db.add(q)

    try:
        await db.commit()
        await db.refresh(q)
    except Exception as e:
        await db.rollback()
        logger.error("报价单更新失败 | id=%d error=%s", quote_id, str(e))
        raise HTTPException(status_code=500, detail="报价单更新失败")

    after = {
        "title": q.title, "estimate_days": q.estimate_days,
        "daily_rate": str(q.daily_rate) if q.daily_rate else None,
        "total_amount": str(q.total_amount), "status": q.status,
    }
    await _record_change(db, quote_id, "field_update", before, after)
    await db.commit()

    return QuotationResponse.model_validate(q)


@router.patch("/{quote_id}", response_model=QuotationResponse)
async def patch_quotation(
    quote_id: int,
    quotation_in: QuotationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await update_quotation(quote_id, quotation_in, db, current_user)


@router.delete("/{quote_id}")
async def delete_quotation(
    quote_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = await quotation_crud.get(db, quote_id)
    if not q:
        raise HTTPException(status_code=404, detail="报价单不存在")
    if not _can_delete(q):
        raise HTTPException(status_code=400, detail="仅草稿状态可删除")
    await quotation_crud.remove(db, quote_id)
    return {"message": "报价单已删除"}


# ── 状态流转接口 ──────────────────────────────────────────

@router.post("/{quote_id}/send", response_model=QuotationResponse)
async def send_quotation(
    quote_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await update_quotation(
        quote_id, QuotationUpdate(status="sent"), db, current_user
    )


@router.post("/{quote_id}/accept", response_model=QuotationResponse)
async def accept_quotation(
    quote_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await update_quotation(
        quote_id, QuotationUpdate(status="accepted"), db, current_user
    )


@router.post("/{quote_id}/reject", response_model=QuotationResponse)
async def reject_quotation(
    quote_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await update_quotation(
        quote_id, QuotationUpdate(status="rejected"), db, current_user
    )


@router.post("/{quote_id}/cancel", response_model=QuotationResponse)
async def cancel_quotation(
    quote_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await update_quotation(
        quote_id, QuotationUpdate(status="cancelled"), db, current_user
    )


# ── 报价预览接口 ──────────────────────────────────────────

@router.post("/preview", response_model=QuotationPreviewResponse)
async def preview_quotation(
    preview_in: QuotationPreviewRequest,
    current_user: User = Depends(get_current_user),
):
    """纯计算预览，不写库。"""
    amounts = _calculate_quote_amount(
        estimate_days=preview_in.estimate_days,
        daily_rate=preview_in.daily_rate,
        direct_cost=preview_in.direct_cost,
        risk_buffer_rate=preview_in.risk_buffer_rate,
        discount_amount=preview_in.discount_amount,
        tax_rate=preview_in.tax_rate,
    )
    return QuotationPreviewResponse(**amounts)


# ── 明细项接口 ────────────────────────────────────────────

@router.get("/{quote_id}/items", response_model=list[QuotationItemResponse])
async def list_quotation_items(
    quote_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(QuotationItem)
        .where(QuotationItem.quotation_id == quote_id)
        .order_by(QuotationItem.sort_order)
    )
    items = result.scalars().all()
    return [QuotationItemResponse.model_validate(item) for item in items]


@router.post("/{quote_id}/items", response_model=QuotationItemResponse, status_code=201)
async def create_quotation_item(
    quote_id: int,
    item_in: QuotationItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = await quotation_crud.get(db, quote_id)
    if not q:
        raise HTTPException(status_code=404, detail="报价单不存在")

    amount = round(item_in.quantity * item_in.unit_price, QUOTE_DECIMAL_PLACES)
    item = QuotationItem(
        quotation_id=quote_id,
        item_name=item_in.item_name,
        item_type=item_in.item_type,
        quantity=item_in.quantity,
        unit_price=item_in.unit_price,
        amount=amount,
        notes=item_in.notes,
        sort_order=item_in.sort_order,
        created_at=datetime.utcnow(),
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return QuotationItemResponse.model_validate(item)


# ── 报价转合同接口 ────────────────────────────────────────

@router.post("/{quote_id}/convert-to-contract", response_model=QuotationResponse)
async def convert_to_contract(
    quote_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = await quotation_crud.get(db, quote_id)
    if not q:
        raise HTTPException(status_code=404, detail="报价单不存在")
    if q.status != "accepted":
        raise HTTPException(status_code=400, detail="仅已接受的报价单可转为合同")
    if q.converted_contract_id:
        raise HTTPException(status_code=400, detail="该报价单已转为合同")

    before = {"status": q.status, "converted_contract_id": None}
    contract_no = await contract_crud.generate_contract_no(db)

    new_contract = Contract(
        contract_no=contract_no,
        customer_id=q.customer_id,
        title=q.title,
        amount=float(q.total_amount) if q.total_amount else 0,
        status="draft",
        terms=q.requirement_summary,
        quotation_id=q.id,
    )
    db.add(new_contract)
    await db.flush()

    q.converted_contract_id = new_contract.id
    db.add(q)
    await db.flush()

    after = {"status": q.status, "converted_contract_id": new_contract.id}
    await _record_change(db, quote_id, "converted", before, after)

    try:
        await db.commit()
        await db.refresh(q)
        await db.refresh(new_contract)
    except Exception as e:
        await db.rollback()
        logger.error("报价转合同失败 | quote_id=%d error=%s", quote_id, str(e))
        raise HTTPException(status_code=500, detail="报价转合同失败")

    return QuotationResponse.model_validate(q)
