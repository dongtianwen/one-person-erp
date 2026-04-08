"""FR-501 需求版本管理与需求变更记录 API 路由
v1.7 变更冻结机制——需求冻结状态下直接修改返回 HTTP 409
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.requirement import Requirement, RequirementChange
from app.core.requirement_utils import set_requirement_as_current, can_modify_field
from app.core.change_order_utils import is_project_requirements_frozen

from app.schemas.requirement import (
    RequirementCreate,
    RequirementUpdate,
    RequirementResponse,
    RequirementDetailResponse,
    RequirementListItem,
    RequirementChangeCreate,
    RequirementChangeResponse,
)

router = APIRouter()


# ── 需求版本 CRUD ─────────────────────────────────────────────────


@router.get("", response_model=list[RequirementListItem])
async def list_requirements(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """返回该项目所有需求版本，按 created_at 倒序"""
    project = await db.get(Project, project_id)
    if not project or project.is_deleted:
        raise HTTPException(status_code=404, detail="项目不存在")

    result = await db.execute(
        select(Requirement)
        .where(Requirement.project_id == project_id, Requirement.is_deleted == False)
        .order_by(Requirement.created_at.desc())
    )
    items = result.scalars().all()
    return items


@router.get("/{requirement_id}", response_model=RequirementDetailResponse)
async def get_requirement(
    project_id: int,
    requirement_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """返回需求版本详情，包含 changes 数组"""
    req = await db.get(Requirement, requirement_id)
    if not req or req.is_deleted or req.project_id != project_id:
        raise HTTPException(status_code=404, detail="需求版本不存在")

    # 获取变更记录
    changes_result = await db.execute(
        select(RequirementChange)
        .where(RequirementChange.requirement_id == requirement_id)
        .order_by(RequirementChange.created_at.desc())
    )
    changes = list(changes_result.scalars().all())

    return {
        "id": req.id,
        "project_id": req.project_id,
        "version_no": req.version_no,
        "summary": req.summary,
        "confirm_status": req.confirm_status,
        "confirmed_at": req.confirmed_at,
        "confirm_method": req.confirm_method,
        "is_current": req.is_current,
        "notes": req.notes,
        "created_at": req.created_at,
        "updated_at": req.updated_at,
        "changes": [RequirementChangeResponse.model_validate(c) for c in changes],
    }


@router.post("", response_model=RequirementResponse, status_code=201)
async def create_requirement(
    project_id: int,
    req_in: RequirementCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建需求版本。新版本 is_current 默认为 True，同项目其他版本设为 False。"""
    project = await db.get(Project, project_id)
    if not project or project.is_deleted:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 如果新版本设为 current，先清除同项目其他版本
    if req_in.is_current:
        from sqlalchemy import update as sa_update
        await db.execute(
            sa_update(Requirement)
            .where(Requirement.project_id == project_id, Requirement.is_deleted == False)
            .values(is_current=False)
        )

    req = Requirement(
        project_id=project_id,
        version_no=req_in.version_no,
        summary=req_in.summary,
        is_current=req_in.is_current,
        notes=req_in.notes,
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)
    return req


@router.put("/{requirement_id}", response_model=RequirementResponse)
async def update_requirement(
    project_id: int,
    requirement_id: int,
    req_in: RequirementUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """全量更新。confirmed 状态下 summary/version_no 不可修改

    v1.7: 如果项目需求已冻结，直接修改返回 HTTP 409
    """
    req = await db.get(Requirement, requirement_id)
    if not req or req.is_deleted or req.project_id != project_id:
        raise HTTPException(status_code=404, detail="需求版本不存在")

    # v1.7: 检查需求是否冻结
    if await is_project_requirements_frozen(db, project_id):
        raise HTTPException(
            status_code=409,
            detail="需求已冻结，请通过变更单提交"
        )

    # 字段修改约束
    update_data = req_in.model_dump(exclude_unset=True)
    for field_name in update_data:
        if not can_modify_field(req.confirm_status, field_name):
            raise HTTPException(status_code=422, detail="已确认的需求版本不可修改内容")

    for field, value in update_data.items():
        setattr(req, field, value)

    await db.commit()
    await db.refresh(req)
    return req


@router.patch("/{requirement_id}", response_model=RequirementResponse)
async def patch_requirement(
    project_id: int,
    requirement_id: int,
    req_in: RequirementUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """部分更新。confirmed 状态下 summary/version_no 不可修改（PATCH 不豁免）"""
    return await update_requirement(project_id, requirement_id, req_in, db, current_user)


@router.post("/{requirement_id}/set-current", response_model=RequirementResponse)
async def set_current(
    project_id: int,
    requirement_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """将指定版本设为当前有效版本"""
    req = await db.get(Requirement, requirement_id)
    if not req or req.is_deleted or req.project_id != project_id:
        raise HTTPException(status_code=404, detail="需求版本不存在")

    await set_requirement_as_current(requirement_id, project_id, db)
    await db.commit()
    await db.refresh(req)
    return req


# ── 需求变更记录 ─────────────────────────────────────────────────


@router.post("/{requirement_id}/changes", response_model=RequirementChangeResponse, status_code=201)
async def create_change(
    project_id: int,
    requirement_id: int,
    change_in: RequirementChangeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建变更记录。is_billable=True 且 change_order_id 为 NULL 时返回 422"""
    req = await db.get(Requirement, requirement_id)
    if not req or req.is_deleted or req.project_id != project_id:
        raise HTTPException(status_code=404, detail="需求版本不存在")

    if change_in.is_billable and change_in.change_order_id is None:
        raise HTTPException(status_code=422, detail="收费变更必须先关联或创建变更单")

    change = RequirementChange(
        requirement_id=requirement_id,
        title=change_in.title,
        description=change_in.description,
        change_type=change_in.change_type,
        is_billable=change_in.is_billable,
        change_order_id=change_in.change_order_id,
        initiated_by=change_in.initiated_by,
    )
    db.add(change)
    await db.commit()
    await db.refresh(change)
    return change
