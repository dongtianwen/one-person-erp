"""v2.2 snapshot 底座服务——统一快照创建/查询/版本对比。

核心函数：
- create_snapshot: 创建快照，原子 is_latest 切换
- get_latest_snapshot: 获取最新快照
- get_snapshot_history: 获取完整快照链
- save_with_snapshot: 主业务保存 + 触发快照
- get_version_diff: 两个版本对比
"""

import json
import logging
from typing import Any, Callable, Awaitable

from pydantic import RootModel, ValidationError
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entity_snapshot import EntitySnapshot
from app.core.constants import WARNING_SNAPSHOT_WRITE_FAILED

logger = logging.getLogger(__name__)


class SnapshotJsonModel(RootModel[dict[str, Any]]):
    """snapshot_json 入库前 pydantic 校验模型。"""
    pass


async def create_snapshot(
    db: AsyncSession,
    entity_type: str,
    entity_id: int,
    snapshot_json: dict[str, Any] | str,
) -> tuple[bool, str | None]:
    """创建快照。

    返回 (True, None) 表示成功；
    返回 (False, warning_code) 表示失败，不抛异常。
    """
    try:
        if isinstance(snapshot_json, str):
            raise ValueError("snapshot_json must be a dict, not a string")

        SnapshotJsonModel.model_validate(snapshot_json)

        result = await db.execute(
            select(func.max(EntitySnapshot.version_no)).where(
                EntitySnapshot.entity_type == entity_type,
                EntitySnapshot.entity_id == entity_id,
            )
        )
        max_version = result.scalar() or 0
        new_version = max_version + 1

        latest_row = await db.execute(
            select(EntitySnapshot).where(
                EntitySnapshot.entity_type == entity_type,
                EntitySnapshot.entity_id == entity_id,
                EntitySnapshot.is_latest.is_(True),
            )
        )
        latest_snapshot = latest_row.scalar_one_or_none()
        parent_id = latest_snapshot.id if latest_snapshot else None

        if latest_snapshot:
            await db.execute(
                update(EntitySnapshot)
                .where(EntitySnapshot.id == latest_snapshot.id)
                .values(is_latest=False)
            )

        snapshot = EntitySnapshot(
            entity_type=entity_type,
            entity_id=entity_id,
            version_no=new_version,
            snapshot_json=json.dumps(snapshot_json, ensure_ascii=False),
            parent_snapshot_id=parent_id,
            is_latest=True,
        )
        db.add(snapshot)
        await db.commit()
        await db.refresh(snapshot)
        return True, None

    except (ValueError, ValidationError) as e:
        logger.warning(
            "snapshot_json 校验失败 | entity_type=%s entity_id=%s error=%s",
            entity_type, entity_id, e,
        )
        await db.rollback()
        return False, WARNING_SNAPSHOT_WRITE_FAILED
    except Exception as e:
        logger.error(
            "快照写入失败 | entity_type=%s entity_id=%s error=%s",
            entity_type, entity_id, e,
        )
        await db.rollback()
        return False, WARNING_SNAPSHOT_WRITE_FAILED


async def get_latest_snapshot(
    db: AsyncSession,
    entity_type: str,
    entity_id: int,
) -> dict[str, Any] | None:
    """获取指定实体的最新快照。"""
    result = await db.execute(
        select(EntitySnapshot).where(
            EntitySnapshot.entity_type == entity_type,
            EntitySnapshot.entity_id == entity_id,
            EntitySnapshot.is_latest.is_(True),
        )
    )
    snapshot = result.scalar_one_or_none()
    if snapshot is None:
        return None
    return _to_dict(snapshot)


async def get_snapshot_history(
    db: AsyncSession,
    entity_type: str,
    entity_id: int,
) -> list[dict[str, Any]]:
    """获取指定实体的完整快照链，按 version_no 升序。"""
    result = await db.execute(
        select(EntitySnapshot)
        .where(
            EntitySnapshot.entity_type == entity_type,
            EntitySnapshot.entity_id == entity_id,
        )
        .order_by(EntitySnapshot.version_no.asc())
    )
    snapshots = result.scalars().all()
    return [_to_dict(s) for s in snapshots]


async def save_with_snapshot(
    db: AsyncSession,
    entity_type: str,
    entity_id: int,
    snapshot_json: dict[str, Any] | str,
    db_save_fn: Callable[[AsyncSession], Awaitable[None]],
) -> tuple[bool, str | None]:
    """执行主业务保存，成功后触发 snapshot 写入。

    snapshot 失败时返回 warning_code，不阻断主流程。
    """
    try:
        await db_save_fn(db)
        await db.commit()
    except Exception as e:
        logger.error("主业务保存失败 | entity_type=%s entity_id=%s error=%s", entity_type, entity_id, e)
        await db.rollback()
        raise

    success, warning_code = await create_snapshot(db, entity_type, entity_id, snapshot_json)
    if not success:
        return True, warning_code

    return True, None


async def get_version_diff(
    db: AsyncSession,
    entity_type: str,
    entity_id: int,
    version_a: int,
    version_b: int,
) -> dict[str, Any]:
    """返回两个版本的 snapshot_json，供前端展示对比。"""
    result = await db.execute(
        select(EntitySnapshot).where(
            EntitySnapshot.entity_type == entity_type,
            EntitySnapshot.entity_id == entity_id,
            EntitySnapshot.version_no.in_([version_a, version_b]),
        )
    )
    snapshots = result.scalars().all()
    version_map = {s.version_no: s for s in snapshots}

    if version_a not in version_map or version_b not in version_map:
        from app.core.error_codes import ERROR_CODES
        raise ValueError(ERROR_CODES.get("SNAPSHOT_VERSION_NOT_FOUND", "版本不存在"))

    return {
        "version_a": {
            "version_no": version_map[version_a].version_no,
            "content": json.loads(version_map[version_a].snapshot_json),
        },
        "version_b": {
            "version_no": version_map[version_b].version_no,
            "content": json.loads(version_map[version_b].snapshot_json),
        },
    }


def _to_dict(snapshot: EntitySnapshot) -> dict[str, Any]:
    return {
        "id": snapshot.id,
        "entity_type": snapshot.entity_type,
        "entity_id": snapshot.entity_id,
        "version_no": snapshot.version_no,
        "snapshot_json": json.loads(snapshot.snapshot_json),
        "parent_snapshot_id": snapshot.parent_snapshot_id,
        "is_latest": snapshot.is_latest,
        "created_at": snapshot.created_at.isoformat() if snapshot.created_at else None,
    }
