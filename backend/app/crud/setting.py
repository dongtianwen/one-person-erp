from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.setting import SystemSetting


async def get_setting(db: AsyncSession, key: str) -> str | None:
    result = await db.execute(select(SystemSetting).where(SystemSetting.key == key, SystemSetting.is_deleted == False))
    setting = result.scalar_one_or_none()
    return setting.value if setting else None


async def set_setting(db: AsyncSession, key: str, value: str) -> None:
    result = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
    setting = result.scalar_one_or_none()
    if setting:
        setting.value = value
    else:
        setting = SystemSetting(key=key, value=value)
        db.add(setting)


async def delete_setting(db: AsyncSession, key: str) -> None:
    result = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
    setting = result.scalar_one_or_none()
    if setting:
        setting.is_deleted = True
