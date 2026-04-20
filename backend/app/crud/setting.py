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


COMPANY_KEYS = [
    "company_name",
    "company_tax_id",
    "company_address",
    "company_legal_rep",
    "company_contact",
    "company_phone",
    "company_email",
    "company_bank_name",
    "company_bank_account",
]

TAX_CONFIG_KEYS = [
    "tax_payer_type",
    "tax_small_scale_rate",
    "tax_small_scale_exempt_threshold",
    "tax_general_standard_rate",
    "tax_general_include_ordinary_input",
]


async def get_company_settings(db: AsyncSession) -> dict[str, str]:
    """读取所有公司设置项，返回 dict。"""
    result = await db.execute(
        select(SystemSetting).where(
            SystemSetting.key.in_(COMPANY_KEYS),
            SystemSetting.is_deleted == False,
        )
    )
    settings = result.scalars().all()
    return {s.key: s.value for s in settings if s.value}


async def update_company_settings(db: AsyncSession, data: dict[str, str]) -> None:
    """批量更新公司设置（upsert）。"""
    for key in COMPANY_KEYS:
        value = data.get(key, "")
        if value:
            await set_setting(db, key, value)
