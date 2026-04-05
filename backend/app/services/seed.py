"""Seed default data on first startup."""
import json
import logging

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reminder import ReminderSetting
from app.models.file_index import FileIndex

logger = logging.getLogger(__name__)

# Default reminder settings
DEFAULT_REMINDER_SETTINGS = [
    {
        "reminder_type": "annual_report",
        "config": json.dumps({"month": 3, "day": 31}),
        "is_active": True,
    },
    {
        "reminder_type": "tax_filing",
        "config": json.dumps({"day": 15}),
        "is_active": True,
    },
]

# Default file index entries for a new company
DEFAULT_FILE_INDEXES = [
    {
        "file_name": "营业执照正本",
        "file_type": "license",
        "version": "1",
        "is_current": True,
        "note": "公司营业执照正本，需年检更新",
    },
    {
        "file_name": "公司章程",
        "file_type": "charter",
        "version": "1",
        "is_current": True,
        "note": "公司章程及修正案",
    },
    {
        "file_name": "入驻协议/租赁合同",
        "file_type": "agreement",
        "version": "1",
        "is_current": True,
        "note": "办公场地租赁合同",
    },
    {
        "file_name": "税务备案回执",
        "file_type": "tax_record",
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
    """Seed default reminder settings and file indexes if database is empty."""
    # Check if reminder settings already exist
    result = await db.execute(select(func.count(ReminderSetting.id)))
    setting_count = result.scalar() or 0

    if setting_count == 0:
        for setting_data in DEFAULT_REMINDER_SETTINGS:
            setting = ReminderSetting(**setting_data)
            db.add(setting)
        logger.info("Seeded %d default reminder settings", len(DEFAULT_REMINDER_SETTINGS))

    # Check if file indexes already exist
    result = await db.execute(select(func.count(FileIndex.id)))
    file_count = result.scalar() or 0

    if file_count == 0:
        for file_data in DEFAULT_FILE_INDEXES:
            file_index = FileIndex(**file_data)
            db.add(file_index)
        logger.info("Seeded %d default file indexes", len(DEFAULT_FILE_INDEXES))

    await db.commit()
