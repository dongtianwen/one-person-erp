"""Seed default data on first startup with system_initialized lock."""

import json
import logging
import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reminder import ReminderSetting
from app.models.file_index import FileIndex
from app.models.setting import SystemSetting
from app.crud import setting as setting_crud

logger = logging.getLogger(__name__)

DEFAULT_REMINDER_SETTINGS = [
    {
        "reminder_type": "annual_audit",
        "config": json.dumps({"month": 3, "day": 31}),
        "is_active": True,
    },
    {
        "reminder_type": "tax_filing",
        "config": json.dumps({"day": 15}),
        "is_active": True,
    },
]

DEFAULT_FILE_INDEXES = [
    {
        "file_name": "营业执照正本",
        "file_type": "business_license",
        "version": "1",
        "is_current": True,
        "note": "公司营业执照正本，需年检更新",
    },
    {
        "file_name": "公司章程",
        "file_type": "company_charter",
        "version": "1",
        "is_current": True,
        "note": "公司章程及修正案",
    },
    {
        "file_name": "数标园入驻协议",
        "file_type": "lease_agreement",
        "version": "1",
        "is_current": True,
        "note": "办公场地租赁/入驻协议",
    },
    {
        "file_name": "税务备案回执",
        "file_type": "tax_registration",
        "version": "1",
        "is_current": True,
        "note": "税务机关登记备案回执",
    },
    {
        "file_name": "首次审计报告",
        "file_type": "audit_report",
        "version": "1",
        "is_current": True,
        "note": "首次年度审计报告",
    },
]


async def seed_default_data(db: AsyncSession) -> None:
    """Seed default data only if system is not yet initialized."""
    initialized = await setting_crud.get_setting(db, "system_initialized")
    if initialized == "true":
        logger.info("System already initialized, skipping seed")
        return

    # Seed reminder settings
    result = await db.execute(select(func.count(ReminderSetting.id)))
    setting_count = result.scalar() or 0
    if setting_count == 0:
        for setting_data in DEFAULT_REMINDER_SETTINGS:
            setting = ReminderSetting(**setting_data)
            db.add(setting)
        logger.info("Seeded %d default reminder settings", len(DEFAULT_REMINDER_SETTINGS))

    # Seed file indexes with unique file_group_id per entry
    result = await db.execute(select(func.count(FileIndex.id)))
    file_count = result.scalar() or 0
    if file_count == 0:
        for file_data in DEFAULT_FILE_INDEXES:
            file_index = FileIndex(
                file_group_id=str(uuid.uuid4()),
                **file_data,
            )
            db.add(file_index)
        logger.info("Seeded %d default file indexes", len(DEFAULT_FILE_INDEXES))

    # Mark system as initialized
    await setting_crud.set_setting(db, "system_initialized", "true")
    await db.commit()
    logger.info("System initialization complete")
