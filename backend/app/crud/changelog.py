from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.changelog import ChangeLog


async def create_changelog(
    db: AsyncSession,
    entity_type: str,
    entity_id: int,
    field: str,
    old_value: str | None,
    new_value: str | None,
    changed_by: int | None = None,
) -> ChangeLog:
    log = ChangeLog(
        entity_type=entity_type,
        entity_id=entity_id,
        field=field,
        old_value=old_value,
        new_value=new_value,
        changed_by=changed_by,
    )
    db.add(log)
    await db.flush()
    return log


async def get_changelogs(
    db: AsyncSession,
    entity_type: str,
    entity_id: int,
) -> list[ChangeLog]:
    result = await db.execute(
        select(ChangeLog)
        .where(
            ChangeLog.entity_type == entity_type,
            ChangeLog.entity_id == entity_id,
            ChangeLog.is_deleted == False,
        )
        .order_by(ChangeLog.created_at.desc())
    )
    return list(result.scalars().all())
