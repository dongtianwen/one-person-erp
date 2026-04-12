"""v1.11 标注任务工具——状态流转校验、规范写入 requirements 表。"""

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    ANNOTATION_TASK_VALID_TRANSITIONS,
    ANNOTATION_SPEC_REQUIREMENT_TYPE,
)
from app.core.logging import get_logger

logger = get_logger("annotation_utils")


def validate_annotation_task_transition(current: str, target: str) -> bool:
    """校验标注任务状态流转是否合法。"""
    allowed = ANNOTATION_TASK_VALID_TRANSITIONS.get(current, [])
    return target in allowed


async def create_annotation_spec(
    db: AsyncSession,
    task_id: int,
    title: str,
    content: str,
    notes: str | None = None,
) -> dict[str, Any]:
    """创建标注规范——写入 requirements 表（requirement_type=annotation_spec）。"""
    from app.models.requirement import Requirement
    from app.models.annotation_task import AnnotationTask

    task = await db.get(AnnotationTask, task_id)
    if not task:
        raise ValueError(f"标注任务 {task_id} 不存在")

    req = Requirement(
        project_id=task.project_id,
        version_no=title,
        summary=content,
        requirement_type=ANNOTATION_SPEC_REQUIREMENT_TYPE,
        annotation_task_id=task_id,
        notes=notes,
    )
    db.add(req)
    await db.flush()
    logger.info("标注规范已写入 requirements 表: task_id=%d, req_id=%d", task_id, req.id)
    return {"id": req.id, "title": title}


async def get_task_specs(db: AsyncSession, task_id: int) -> list[dict[str, Any]]:
    """获取标注任务关联的规范列表。"""
    from app.models.requirement import Requirement

    stmt = select(Requirement).where(
        Requirement.annotation_task_id == task_id,
        Requirement.requirement_type == ANNOTATION_SPEC_REQUIREMENT_TYPE,
    ).order_by(Requirement.created_at.desc())
    result = await db.execute(stmt)
    specs = result.scalars().all()
    return [
        {
            "id": s.id,
            "title": s.version_no,
            "content": s.summary,
            "notes": s.notes,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in specs
    ]


async def complete_quality_check(
    db: AsyncSession,
    task_id: int,
    result_text: str,
    passed: bool,
) -> dict[str, Any]:
    """完成质检——原子事务更新质检结果和状态。"""
    from app.models.annotation_task import AnnotationTask

    task = await db.get(AnnotationTask, task_id)
    if not task:
        raise ValueError(f"标注任务 {task_id} 不存在")

    target_status = "completed" if passed else "rework"
    if not validate_annotation_task_transition(task.status, target_status):
        raise ValueError(f"不允许从 {task.status} 转为 {target_status}")

    task.quality_check_result = result_text
    task.status = target_status
    if passed:
        task.completed_at = datetime.utcnow()
    await db.flush()

    logger.info("标注任务 %d 质检完成: result=%s, status=%s", task_id, result_text, target_status)
    return {
        "id": task.id,
        "status": task.status,
        "quality_check_result": task.quality_check_result,
    }
