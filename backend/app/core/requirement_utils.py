"""v1.5 需求与变更管理核心工具函数。"""
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.models.requirement import Requirement
from datetime import datetime

logger = logging.getLogger(__name__)


async def set_requirement_as_current(
    requirement_id: int, project_id: int, db: AsyncSession
) -> None:
    """
    在同一事务中将指定需求版本设为当前有效，同项目其他版本 is_current 设为 False。
    事务失败时全部回滚。
    记录切换操作日志（project_id / 旧版本ID / 新版本ID）。
    """
    # 1. 查找当前有效版本
    result = await db.execute(
        select(Requirement).where(
            Requirement.project_id == project_id,
            Requirement.is_current == True,
            Requirement.is_deleted == False,
        )
    )
    old_req = result.scalar_one_or_none()
    old_id = old_req.id if old_req else None

    # 2. 同项目其他版本设为 False
    await db.execute(
        update(Requirement)
        .where(
            Requirement.project_id == project_id,
            Requirement.id != requirement_id,
            Requirement.is_deleted == False,
        )
        .values(is_current=False)
    )
    # 3. 设置目标版本为 True
    await db.execute(
        update(Requirement)
        .where(Requirement.id == requirement_id)
        .values(is_current=True)
    )
    await db.flush()

    logger.info(
        "需求版本切换 | action=set_requirement_as_current | table=requirements | "
        "project_id=%s | old_version_id=%s | new_version_id=%s",
        project_id, old_id, requirement_id,
    )


def can_modify_field(requirement_status: str, field_name: str) -> bool:
    """
    confirmed 状态下，summary 和 version_no 不可修改，其他字段或其他状态下返回 True。
    """
    if requirement_status != "confirmed":
        return True
    return field_name not in ("summary", "version_no")
