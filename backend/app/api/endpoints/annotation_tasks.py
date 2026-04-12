"""v1.11 标注任务 CRUD API 路由。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.annotation_task import AnnotationTask
from app.models.dataset import DatasetVersion
from app.core.constants import ANNOTATION_TASK_STATUS_WHITELIST
from app.core.annotation_utils import (
    validate_annotation_task_transition,
    create_annotation_spec,
    get_task_specs,
    complete_quality_check,
)
from app.core.error_codes import ERROR_CODES

router = APIRouter()


@router.post("")
async def create_task(
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建标注任务（project_id 和 dataset_version_id 必填）。"""
    project_id = data.get("project_id")
    dv_id = data.get("dataset_version_id")
    if not project_id or not dv_id:
        raise HTTPException(status_code=422, detail="project_id 和 dataset_version_id 必填")

    dv = await db.get(DatasetVersion, dv_id)
    if not dv:
        raise HTTPException(status_code=404, detail="数据集版本不存在")

    task = AnnotationTask(
        project_id=project_id,
        dataset_version_id=dv_id,
        name=data["name"],
        batch_no=data.get("batch_no"),
        sample_count=data.get("sample_count"),
        annotator_count=data.get("annotator_count"),
        assignee=data.get("assignee"),
        deadline=data.get("deadline"),
        progress=data.get("progress"),
        notes=data.get("notes"),
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return {"id": task.id, "message": "创建成功"}


@router.get("")
async def list_tasks(
    project_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取标注任务列表。"""
    stmt = select(AnnotationTask)
    if project_id:
        stmt = stmt.where(AnnotationTask.project_id == project_id)
    stmt = stmt.order_by(AnnotationTask.created_at.desc())
    result = await db.execute(stmt)
    tasks = result.scalars().all()
    data_list = []
    for t in tasks:
        item = {
            "id": t.id,
            "project_id": t.project_id,
            "dataset_version_id": t.dataset_version_id,
            "name": t.name,
            "status": t.status,
            "batch_no": t.batch_no,
            "sample_count": t.sample_count,
            "annotator_count": t.annotator_count,
            "assignee": t.assignee,
            "deadline": t.deadline.isoformat() if t.deadline else None,
            "progress": t.progress,
            "quality_check_result": t.quality_check_result,
            "rework_reason": t.rework_reason,
            "completed_at": t.completed_at.isoformat() if t.completed_at else None,
            "notes": t.notes,
        }
        data_list.append(item)
    return {"data": data_list}


@router.get("/{task_id}")
async def get_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取标注任务详情。"""
    task = await db.get(AnnotationTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail=ERROR_CODES["NOT_FOUND"])
    return {
        "id": task.id,
        "project_id": task.project_id,
        "dataset_version_id": task.dataset_version_id,
        "name": task.name,
        "status": task.status,
        "batch_no": task.batch_no,
        "sample_count": task.sample_count,
        "annotator_count": task.annotator_count,
        "assignee": task.assignee,
        "deadline": task.deadline.isoformat() if task.deadline else None,
        "progress": task.progress,
        "quality_check_result": task.quality_check_result,
        "rework_reason": task.rework_reason,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "notes": task.notes,
    }


@router.put("/{task_id}")
async def update_task(
    task_id: int,
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新标注任务信息。"""
    task = await db.get(AnnotationTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail=ERROR_CODES["NOT_FOUND"])

    for field in ("name", "batch_no", "sample_count", "annotator_count", "assignee", "deadline", "progress", "notes"):
        if field in data:
            setattr(task, field, data[field])

    await db.commit()
    return {"message": "更新成功"}


@router.delete("/{task_id}")
async def delete_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除标注任务。"""
    task = await db.get(AnnotationTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail=ERROR_CODES["NOT_FOUND"])

    await db.delete(task)
    await db.commit()
    return {"message": "删除成功"}


# ── 状态转换 ─────────────────────────────────────────────────────


@router.patch("/{task_id}/status")
async def transition_status(
    task_id: int,
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """标注任务状态流转。rework 时 rework_reason 必填。"""
    task = await db.get(AnnotationTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail=ERROR_CODES["NOT_FOUND"])

    target = data.get("status")
    if not target or target not in ANNOTATION_TASK_STATUS_WHITELIST:
        raise HTTPException(status_code=422, detail="目标状态不合法")

    if not validate_annotation_task_transition(task.status, target):
        raise HTTPException(status_code=409, detail=f"不允许从 {task.status} 转为 {target}")

    # rework 时 rework_reason 必填
    if target == "rework" and not data.get("rework_reason"):
        raise HTTPException(status_code=422, detail="rework_reason 必填")

    task.status = target
    if data.get("rework_reason"):
        task.rework_reason = data["rework_reason"]
    if target == "completed":
        from datetime import datetime
        task.completed_at = datetime.utcnow()

    await db.commit()
    return {"message": f"状态已更新为 {target}"}


# ── 标注规范 ─────────────────────────────────────────────────────


@router.post("/{task_id}/specs")
async def create_spec(
    task_id: int,
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建标注规范——写入 requirements 表。"""
    title = data.get("title")
    content = data.get("content")
    if not title or not content:
        raise HTTPException(status_code=422, detail="title 和 content 必填")

    try:
        result = await create_annotation_spec(
            db, task_id, title, content, data.get("notes"),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    await db.commit()
    return {"id": result["id"], "message": "标注规范已创建"}


@router.get("/{task_id}/specs")
async def list_specs(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取标注任务的规范列表。"""
    return await get_task_specs(db, task_id)
