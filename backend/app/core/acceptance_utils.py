"""FR-502 验收管理核心工具函数——严格对齐 prd1_5.md 簇 C"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import date
import logging

from app.core.constants import NOTES_SEPARATOR
from app.models.reminder import Reminder

logger = logging.getLogger(__name__)


async def create_payment_reminder_for_acceptance(
    acceptance_name: str, acceptance_id: int, db: AsyncSession
) -> int:
    """
    创建收款提醒，返回 reminder_id。
    必须在调用方事务中执行，不得单独提交。
    title = "收款提醒：{acceptance_name}"
    """
    reminder = Reminder(
        title=f"收款提醒：{acceptance_name}",
        reminder_type="custom",
        is_critical=False,
        status="pending",
        reminder_date=date.today(),
        entity_type="acceptance",
        entity_id=acceptance_id,
        source="auto",
    )
    db.add(reminder)
    await db.flush()
    logger.info(
        "验收联动收款提醒 | action=create_payment_reminder | "
        "acceptance_id=%s | reminder_id=%s",
        acceptance_id, reminder.id,
    )
    return reminder.id


def append_notes(existing_notes: str | None, new_note: str) -> str:
    """
    追加 notes，使用 NOTES_SEPARATOR 分隔。
    existing_notes 为 None 或空字符串时直接返回 new_note。
    """
    if not existing_notes:
        return new_note
    return existing_notes + NOTES_SEPARATOR + new_note
