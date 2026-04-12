"""FR-505 项目维度变更单摘要（只读）——挂载在 /api/v1/projects/{project_id}/change-orders
v1.7 变更冻结机制——项目维度变更单 CRUD + 状态流转
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, date
from typing import Optional

import sqlite3

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.contract import Contract
from app.models.change_order import ChangeOrder
from app.schemas.change_order import ChangeOrderSummaryItem
from app.core.change_order_utils import (
    is_project_requirements_frozen_sync,
    validate_change_order_transition_v17,
    confirm_change_order_sync,
    reject_change_order_sync,
)

logger = logging.getLogger("app.project_change_orders")
router = APIRouter()


# ── v1.7 项目维度变更单 CRUD ───────────────────────────────────


@router.post("", response_model=dict, status_code=201)
async def create_project_change_order(
    project_id: int,
    order_data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建项目变更单（v1.7）。

    如果项目需求已冻结，必须通过变更单进行需求修改。
    """
    project = await db.get(Project, project_id)
    if not project or project.is_deleted:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 使用同步数据库连接检查需求冻结状态
    import os
    db_path = os.path.join(os.getcwd(), "shubiao.db")
    if not os.path.exists(db_path):
        db_path = os.path.join(os.getcwd(), "backend", "shubiao.db")
    sync_db = sqlite3.connect(db_path)
    try:
        is_frozen = is_project_requirements_frozen_sync(sync_db, project_id)
        if is_frozen:
            logger.info(f"项目 {project_id} 需求已冻结，创建变更单")

        # 生成变更单编号
        from app.core.change_order_utils import generate_change_order_no
        order_no = await generate_change_order_no(db)

        # 创建变更单（简化版，实际应使用 Pydantic schema）
        cur = sync_db.cursor()
        cur.execute("""
            INSERT INTO change_orders (
                order_no, contract_id, title, description,
                amount, status, notes, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            order_no,
            order_data.get("contract_id"),
            order_data.get("title", ""),
            order_data.get("description", ""),
            order_data.get("extra_amount", 0),
            "pending",
            order_data.get("notes"),
            datetime.now(),
            datetime.now(),
        ))
        sync_db.commit()
        co_id = cur.lastrowid

        return {"id": co_id, "order_no": order_no, "status": "pending"}
    finally:
        sync_db.close()


@router.get("")
async def list_project_change_orders(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取项目的所有变更单列表（v1.7）。"""
    project = await db.get(Project, project_id)
    if not project or project.is_deleted:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 使用同步数据库查询
    import os
    db_path = os.path.join(os.getcwd(), "shubiao.db")
    if not os.path.exists(db_path):
        db_path = os.path.join(os.getcwd(), "backend", "shubiao.db")
    sync_db = sqlite3.connect(db_path)
    try:
        cur = sync_db.cursor()
        cur.execute("""
            SELECT co.id, co.order_no, co.title, co.description,
                   co.amount as extra_amount, co.status, co.extra_days,
                   co.client_confirmed_at, co.created_at, co.updated_at
            FROM change_orders co
            JOIN contracts c ON co.contract_id = c.id
            WHERE c.project_id = ? AND co.is_deleted = 0
            ORDER BY co.created_at DESC
        """, (project_id,))
        orders = cur.fetchall()

        # 检查需求是否冻结
        is_frozen = is_project_requirements_frozen_sync(sync_db, project_id)

        return {
            "data": [
                {
                    "id": row[0],
                    "order_no": row[1],
                    "title": row[2],
                    "description": row[3],
                    "extra_amount": row[4],
                    "status": row[5],
                    "extra_days": row[6],
                    "client_confirmed_at": row[7] if len(row) > 7 else None,
                    "created_at": row[8] if len(row) > 8 else row[7] if len(row) > 7 else None,
                    "updated_at": row[9] if len(row) > 9 else row[8] if len(row) > 8 else None,
                }
                for row in orders
            ],
            "is_frozen": is_frozen,
        }
    finally:
        sync_db.close()


@router.get("/summary", response_model=list[ChangeOrderSummaryItem])
async def project_change_order_summary(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """项目维度变更单摘要（只读，职责分离）。展示关联合同的变更单，无写操作"""
    project = await db.get(Project, project_id)
    if not project or project.is_deleted:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 查找该项目所有关联合同
    contracts_result = await db.execute(
        select(Contract.id, Contract.contract_no).where(
            Contract.project_id == project_id,
            Contract.is_deleted == False,
        )
    )
    contracts = {cid: cno for cid, cno in contracts_result.all()}

    if not contracts:
        return []

    # 查找这些合同的所有变更单
    orders_result = await db.execute(
        select(ChangeOrder)
        .where(ChangeOrder.contract_id.in_(contracts.keys()))
        .order_by(ChangeOrder.created_at.desc())
    )
    orders = list(orders_result.scalars().all())

    return [
        ChangeOrderSummaryItem(
            order_no=o.order_no,
            title=o.title,
            amount=o.amount,
            status=o.status,
            contract_id=o.contract_id,
            contract_no=contracts.get(o.contract_id),
        )
        for o in orders
    ]


# ── v1.7 变更单状态流转 ───────────────────────────────────────────


@router.get("/{co_id}")
async def get_change_order_detail(
    project_id: int,
    co_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取变更单详情（v1.7）。"""
    import os
    db_path = os.path.join(os.getcwd(), "shubiao.db")
    if not os.path.exists(db_path):
        db_path = os.path.join(os.getcwd(), "backend", "shubiao.db")
    sync_db = sqlite3.connect(db_path)
    try:
        cur = sync_db.cursor()
        cur.execute("""
            SELECT co.id, co.order_no, co.title, co.description,
                   co.amount as extra_amount, co.status, co.extra_days,
                   co.client_confirmed_at, co.client_rejected_at,
                   co.rejection_reason, co.created_at
            FROM change_orders co
            JOIN contracts c ON co.contract_id = c.id
            WHERE c.project_id = ? AND co.id = ? AND co.is_deleted = 0
        """, (project_id, co_id))
        row = cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="变更单不存在")

        return {
            "id": row[0],
            "order_no": row[1],
            "title": row[2],
            "description": row[3],
            "extra_amount": row[4],
            "status": row[5],
            "extra_days": row[6],
            "client_confirmed_at": row[7],
            "client_rejected_at": row[8],
            "rejection_reason": row[9],
            "created_at": row[10],
        }
    finally:
        sync_db.close()


@router.patch("/{co_id}/confirm")
async def confirm_change_order(
    project_id: int,
    co_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """客户确认变更单（v1.7）。"""
    import os
    db_path = os.path.join(os.getcwd(), "shubiao.db")
    if not os.path.exists(db_path):
        db_path = os.path.join(os.getcwd(), "backend", "shubiao.db")
    sync_db = sqlite3.connect(db_path)
    try:
        result = confirm_change_order_sync(sync_db, co_id, current_user.id if current_user else None)
        sync_db.commit()
        return {
            "client_confirmed_at": result.get("client_confirmed_at"),
            "status": result.get("status")
        }
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    finally:
        sync_db.close()


@router.patch("/{co_id}/reject")
async def reject_change_order(
    project_id: int,
    co_id: int,
    reason: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """客户拒绝变更单（v1.7）。"""
    import os
    db_path = os.path.join(os.getcwd(), "shubiao.db")
    if not os.path.exists(db_path):
        db_path = os.path.join(os.getcwd(), "backend", "shubiao.db")
    sync_db = sqlite3.connect(db_path)
    try:
        result = reject_change_order_sync(sync_db, co_id, reason, current_user.id if current_user else None)
        sync_db.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    finally:
        sync_db.close()


@router.patch("/{co_id}/cancel")
async def cancel_change_order(
    project_id: int,
    co_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """撤销变更单（v1.7）。"""
    import os
    db_path = os.path.join(os.getcwd(), "shubiao.db")
    if not os.path.exists(db_path):
        db_path = os.path.join(os.getcwd(), "backend", "shubiao.db")
    sync_db = sqlite3.connect(db_path)
    try:
        cur = sync_db.cursor()

        # 获取当前状态
        cur.execute("SELECT status FROM change_orders WHERE id = ?", (co_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="变更单不存在")

        current_status = row[0]

        # 校验状态流转
        if not validate_change_order_transition_v17(current_status, "cancelled"):
            raise HTTPException(status_code=422, detail=f"不能从 {current_status} 状态流转到 cancelled")

        # 更新状态
        cur.execute("UPDATE change_orders SET status = 'cancelled' WHERE id = ?", (co_id,))
        sync_db.commit()

        return {"id": co_id, "status": "cancelled"}
    finally:
        sync_db.close()
