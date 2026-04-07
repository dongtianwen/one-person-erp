"""FR-505 变更单/增补单 API 路由——严格对齐 prd1_5.md 簇 F"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.contract import Contract
from app.models.project import Project
from app.models.change_order import ChangeOrder
from app.core.change_order_utils import (
    generate_change_order_no,
    validate_status_transition,
    calculate_actual_receivable,
)
from app.schemas.change_order import (
    ChangeOrderCreate,
    ChangeOrderUpdate,
    ChangeOrderResponse,
    ChangeOrderListResponse,
    ChangeOrderSummaryItem,
)

logger = logging.getLogger("app.change_orders")
router = APIRouter()


# ── 合同维度 CRUD ──────────────────────────────────────────────


@router.get("", response_model=ChangeOrderListResponse)
async def list_change_orders(
    contract_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """返回该合同所有变更单，按 created_at 倒序。追加 confirmed_total / actual_receivable"""
    contract = await db.get(Contract, contract_id)
    if not contract or contract.is_deleted:
        raise HTTPException(status_code=404, detail="合同不存在")

    result = await db.execute(
        select(ChangeOrder)
        .where(ChangeOrder.contract_id == contract_id)
        .order_by(ChangeOrder.created_at.desc())
    )
    items = list(result.scalars().all())

    totals = await calculate_actual_receivable(contract_id, db)

    return ChangeOrderListResponse(
        items=[ChangeOrderResponse.model_validate(i) for i in items],
        confirmed_total=totals["confirmed_total"],
        actual_receivable=totals["actual_receivable"],
    )


@router.get("/{order_id}", response_model=ChangeOrderResponse)
async def get_change_order(
    contract_id: int,
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """返回变更单详情"""
    order = await db.get(ChangeOrder, order_id)
    if not order or order.contract_id != contract_id:
        raise HTTPException(status_code=404, detail="变更单不存在")
    return order


@router.post("", response_model=ChangeOrderResponse, status_code=201)
async def create_change_order(
    contract_id: int,
    order_in: ChangeOrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建变更单，事务中调用 generate_change_order_no() 生成编号"""
    contract = await db.get(Contract, contract_id)
    if not contract or contract.is_deleted:
        raise HTTPException(status_code=404, detail="合同不存在")

    order_no = await generate_change_order_no(db)

    order = ChangeOrder(
        order_no=order_no,
        contract_id=contract_id,
        requirement_change_id=order_in.requirement_change_id,
        title=order_in.title,
        description=order_in.description,
        amount=order_in.amount,
        status="draft",
        notes=order_in.notes,
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)
    return order


@router.put("/{order_id}", response_model=ChangeOrderResponse)
async def update_change_order(
    contract_id: int,
    order_id: int,
    order_in: ChangeOrderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """全量更新。校验字段约束和状态流转"""
    order = await db.get(ChangeOrder, order_id)
    if not order or order.contract_id != contract_id:
        raise HTTPException(status_code=404, detail="变更单不存在")

    update_data = order_in.model_dump(exclude_unset=True)

    # 字段修改约束：confirmed/in_progress/completed 不可改 amount/description
    if order.status in ("confirmed", "in_progress", "completed"):
        if "amount" in update_data or "description" in update_data:
            raise HTTPException(status_code=422, detail="已确认的变更单不可修改金额和描述")

    # 状态流转校验
    if "status" in update_data:
        if not validate_status_transition(order.status, update_data["status"]):
            logger.warning("变更单非法状态流转 | table=change_orders | order_id=%s | current_status=%s | target_status=%s", order_id, order.status, update_data["status"])
            raise HTTPException(
                status_code=422,
                detail=f"状态从 {order.status} 变更为 {update_data['status']} 不被允许",
            )
        if update_data["status"] in ("confirmed",) and order.status != "confirmed":
            update_data["confirmed_at"] = datetime.utcnow()
            update_data.setdefault("confirm_method", "system")

    for field, value in update_data.items():
        setattr(order, field, value)

    await db.commit()
    await db.refresh(order)
    return order


@router.patch("/{order_id}", response_model=ChangeOrderResponse)
async def patch_change_order(
    contract_id: int,
    order_id: int,
    order_in: ChangeOrderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """部分更新。同样校验字段约束和状态流转"""
    return await update_change_order(contract_id, order_id, order_in, db, current_user)


# ── 项目维度摘要（只读）───────────────────────────────────────


@router.get("/summary", response_model=list[ChangeOrderSummaryItem])
async def project_change_order_summary(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """项目维度摘要（只读，职责分离要求）。无写操作入口"""
    # 注意：此端点挂载在 /api/v1/projects/{project_id}/change-orders/summary
    pass  # 在 main.py 中单独注册
