"""FR-503 交付物管理 API 路由——严格对齐 prd1_5.md 簇 D"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.deliverable import Deliverable, AccountHandover
from app.core.deliverable_utils import contains_password_field
from app.schemas.deliverable import (
    DeliverableCreate,
    DeliverableResponse,
    DeliverableDetailResponse,
    AccountHandoverResponse,
)

logger = logging.getLogger("app.deliverables")
router = APIRouter()


@router.get("", response_model=list[DeliverableResponse])
async def list_deliverables(
    project_id: int,
    deliverable_type: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """返回该项目所有交付物，按 delivery_date 倒序。支持 deliverable_type 筛选"""
    project = await db.get(Project, project_id)
    if not project or project.is_deleted:
        raise HTTPException(status_code=404, detail="项目不存在")

    q = select(Deliverable).where(Deliverable.project_id == project_id)
    if deliverable_type:
        q = q.where(Deliverable.deliverable_type == deliverable_type)
    q = q.order_by(Deliverable.delivery_date.desc())

    result = await db.execute(q)
    return list(result.scalars().all())


@router.get("/{deliverable_id}", response_model=DeliverableDetailResponse)
async def get_deliverable(
    project_id: int,
    deliverable_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """返回交付物详情。account_handover 类型时包含 account_handovers 数组"""
    dlv = await db.get(Deliverable, deliverable_id)
    if not dlv or dlv.project_id != project_id:
        raise HTTPException(status_code=404, detail="交付物不存在")

    handovers_result = await db.execute(
        select(AccountHandover).where(AccountHandover.deliverable_id == deliverable_id)
    )
    handovers = list(handovers_result.scalars().all())

    return {
        "id": dlv.id,
        "project_id": dlv.project_id,
        "acceptance_id": dlv.acceptance_id,
        "name": dlv.name,
        "deliverable_type": dlv.deliverable_type,
        "delivery_date": dlv.delivery_date,
        "recipient_name": dlv.recipient_name,
        "delivery_method": dlv.delivery_method,
        "description": dlv.description,
        "storage_location": dlv.storage_location,
        "version_no": dlv.version_no,
        "created_at": dlv.created_at,
        "account_handovers": [AccountHandoverResponse.model_validate(h) for h in handovers],
    }


@router.post("", response_model=DeliverableResponse, status_code=201)
async def create_deliverable(
    project_id: int,
    dlv_in: DeliverableCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建交付物。account_handover 类型时检测密码字段名，事务内写入 handovers"""
    project = await db.get(Project, project_id)
    if not project or project.is_deleted:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 密码字段检测
    if dlv_in.account_handovers:
        for item in dlv_in.account_handovers:
            item_dict = item.model_dump()
            if contains_password_field(item_dict):
                detected_fields = [k for k in item_dict if any(p in k.lower() for p in ("password", "pwd", "secret", "passwd", "token"))]
                logger.warning("账号交接禁止密码字段拦截 | table=account_handovers | deliverable_type=account_handover | intercepted_fields=%s", detected_fields)
                raise HTTPException(status_code=422, detail="账号交接清单禁止存储密码，请仅记录账号名")

    dlv = Deliverable(
        project_id=project_id,
        acceptance_id=dlv_in.acceptance_id,
        name=dlv_in.name,
        deliverable_type=dlv_in.deliverable_type,
        delivery_date=dlv_in.delivery_date,
        recipient_name=dlv_in.recipient_name,
        delivery_method=dlv_in.delivery_method,
        description=dlv_in.description,
        storage_location=dlv_in.storage_location,
        version_no=dlv_in.version_no,
    )
    db.add(dlv)
    await db.flush()

    # 同一事务写入 account_handovers
    if dlv_in.account_handovers:
        for item in dlv_in.account_handovers:
            handover = AccountHandover(
                deliverable_id=dlv.id,
                platform_name=item.platform_name,
                account_name=item.account_name,
                notes=item.notes,
            )
            db.add(handover)

    await db.commit()
    await db.refresh(dlv)
    return dlv


@router.delete("/{deliverable_id}")
async def delete_deliverable():
    """DELETE 返回 HTTP 405，不执行任何操作"""
    raise HTTPException(status_code=405, detail="交付物禁止删除")
