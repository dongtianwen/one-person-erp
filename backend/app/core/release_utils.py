"""FR-504 版本/发布记录核心工具函数——严格对齐 prd1_5.md 簇 E"""
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.models.release import Release

logger = logging.getLogger(__name__)


async def set_release_as_online(release_id: int, project_id: int, db: AsyncSession) -> None:
    """
    在同一事务中将指定发布记录设为当前线上，同项目其他记录 is_current_online 设为 False。
    操作失败时回滚。记录日志：project_id / 旧版本 ID / 新版本 ID。
    """
    # 查找当前线上版本
    result = await db.execute(
        select(Release).where(
            Release.project_id == project_id,
            Release.is_current_online == True,
        )
    )
    old_rel = result.scalar_one_or_none()
    old_id = old_rel.id if old_rel else None

    # 清除同项目其他记录
    await db.execute(
        update(Release)
        .where(
            Release.project_id == project_id,
            Release.id != release_id,
        )
        .values(is_current_online=False)
    )
    # 设置目标为 True
    await db.execute(
        update(Release)
        .where(Release.id == release_id)
        .values(is_current_online=True)
    )
    await db.flush()

    logger.info(
        "版本上线切换 | action=set_release_as_online | table=releases | "
        "project_id=%s | old_version_id=%s | new_version_id=%s",
        project_id, old_id, release_id,
    )
