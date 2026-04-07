"""FR-504 版本/发布记录 API 路由——严格对齐 prd1_5.md 簇 E"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.release import Release
from app.core.release_utils import set_release_as_online
from app.schemas.release import (
    ReleaseCreate,
    ReleaseUpdate,
    ReleaseResponse,
    ReleaseListItem,
)

router = APIRouter()


@router.get("", response_model=list[ReleaseListItem])
async def list_releases(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """返回该项目所有发布记录，按 release_date 倒序。is_current_online=True 标注 is_pinned"""
    project = await db.get(Project, project_id)
    if not project or project.is_deleted:
        raise HTTPException(status_code=404, detail="项目不存在")

    result = await db.execute(
        select(Release)
        .where(Release.project_id == project_id)
        .order_by(Release.release_date.desc())
    )
    items = list(result.scalars().all())
    return [
        {
            **ReleaseResponse.model_validate(r).model_dump(),
            "is_pinned": r.is_current_online,
        }
        for r in items
    ]


@router.get("/{release_id}", response_model=ReleaseResponse)
async def get_release(
    project_id: int,
    release_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """返回发布记录详情"""
    rel = await db.get(Release, release_id)
    if not rel or rel.project_id != project_id:
        raise HTTPException(status_code=404, detail="发布记录不存在")
    return rel


@router.post("", response_model=ReleaseResponse, status_code=201)
async def create_release(
    project_id: int,
    rel_in: ReleaseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建发布记录。is_current_online=True 时事务内清除同项目其他记录"""
    project = await db.get(Project, project_id)
    if not project or project.is_deleted:
        raise HTTPException(status_code=404, detail="项目不存在")

    if rel_in.is_current_online:
        await set_release_as_online.__wrapped__(0, project_id, db) if hasattr(set_release_as_online, '__wrapped__') else None
        from sqlalchemy import update as sa_update
        await db.execute(
            sa_update(Release)
            .where(Release.project_id == project_id)
            .values(is_current_online=False)
        )

    rel = Release(
        project_id=project_id,
        deliverable_id=rel_in.deliverable_id,
        version_no=rel_in.version_no,
        release_date=rel_in.release_date,
        release_type=rel_in.release_type,
        is_current_online=rel_in.is_current_online,
        changelog=rel_in.changelog,
        deploy_env=rel_in.deploy_env,
        notes=rel_in.notes,
    )
    db.add(rel)
    await db.commit()
    await db.refresh(rel)
    return rel


@router.put("/{release_id}", response_model=ReleaseResponse)
async def update_release(
    project_id: int,
    release_id: int,
    rel_in: ReleaseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """全量更新。version_no/release_date 不可修改"""
    rel = await db.get(Release, release_id)
    if not rel or rel.project_id != project_id:
        raise HTTPException(status_code=404, detail="发布记录不存在")

    update_data = rel_in.model_dump(exclude_unset=True)
    if "version_no" in update_data or "release_date" in update_data:
        raise HTTPException(status_code=422, detail="版本号和发布日期不可修改")

    for field, value in update_data.items():
        setattr(rel, field, value)

    await db.commit()
    await db.refresh(rel)
    return rel


@router.patch("/{release_id}", response_model=ReleaseResponse)
async def patch_release(
    project_id: int,
    release_id: int,
    rel_in: ReleaseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """部分更新。version_no/release_date 不可修改（PATCH 同样约束）"""
    return await update_release(project_id, release_id, rel_in, db, current_user)


@router.post("/{release_id}/set-online", response_model=ReleaseResponse)
async def set_online(
    project_id: int,
    release_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """将指定版本设为当前线上版本"""
    rel = await db.get(Release, release_id)
    if not rel or rel.project_id != project_id:
        raise HTTPException(status_code=404, detail="发布记录不存在")

    await set_release_as_online(release_id, project_id, db)
    await db.commit()
    await db.refresh(rel)
    return rel


@router.delete("/{release_id}")
async def delete_release():
    """DELETE 返回 HTTP 405，不执行任何操作"""
    raise HTTPException(status_code=405, detail="发布记录禁止删除")
