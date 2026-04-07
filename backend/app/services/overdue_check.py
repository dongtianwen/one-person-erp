import logging
import time
from datetime import date, timedelta
from typing import Literal

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reminder import Reminder
from app.models.file_index import FileIndex
from app.models.quotation import Quotation
from app.models.customer_asset import CustomerAsset
from app.models.maintenance import MaintenancePeriod
from app.core.constants import MAINTENANCE_REMINDER_DAYS_BEFORE

logger = logging.getLogger("app.overdue_check")

_OVERDUE_CHECK_EXECUTED = False


def _reset_check_flag() -> None:
    """Reset the startup check flag (for testing only)."""
    global _OVERDUE_CHECK_EXECUTED
    _OVERDUE_CHECK_EXECUTED = False


def _apply_throttle(query, mode: str, limit: int = 1000):
    """Apply throttling limit for dashboard mode."""
    if mode == "throttled":
        query = query.limit(limit)
    return query


async def _check_overdue_reminders(db: AsyncSession, mode: str, today: date) -> int:
    """Check 1: Overdue reminders (pending -> overdue)."""
    query = select(Reminder).where(
        Reminder.status == "pending",
        Reminder.reminder_date < today,
        Reminder.is_deleted == False,
    )
    if mode == "throttled":
        window_start = today - timedelta(days=90)
        query = query.where(Reminder.reminder_date >= window_start).limit(1000)

    result = await db.execute(query)
    overdue_reminders = result.scalars().all()
    for r in overdue_reminders:
        r.status = "overdue"
        db.add(r)
    return len(overdue_reminders)


async def _check_expired_quotations(db: AsyncSession, mode: str, today: date) -> int:
    """Check 2: Expired quotations (draft/sent -> expired)."""
    q_query = select(Quotation).where(
        Quotation.status.in_(["draft", "sent"]),
        Quotation.validity_date < today,
        Quotation.is_deleted == False,
    )
    q_query = _apply_throttle(q_query, mode)

    q_result = await db.execute(q_query)
    expired_quotations = q_result.scalars().all()
    for q in expired_quotations:
        q.status = "expired"
        db.add(q)
    return len(expired_quotations)


async def _check_asset_expiry_reminders(db: AsyncSession, mode: str, today: date) -> int:
    """Check 3: Asset expiry reminders (30 days before)."""
    threshold = today + timedelta(days=30)
    query = select(CustomerAsset).where(
        CustomerAsset.expiry_date != None,
        CustomerAsset.expiry_date <= threshold,
        CustomerAsset.expiry_date >= today,
        CustomerAsset.is_deleted == False,
    )
    query = _apply_throttle(query, mode)

    result = await db.execute(query)
    assets = result.scalars().all()
    count = 0
    for asset in assets:
        existing = await db.execute(
            select(func.count()).select_from(Reminder).where(
                Reminder.entity_type == "customer_asset",
                Reminder.entity_id == asset.id,
                Reminder.reminder_type == "asset_expiry",
                Reminder.is_deleted == False,
            )
        )
        if existing.scalar() > 0:
            continue
        db.add(Reminder(
            title=f"客户资产到期: {asset.name}",
            reminder_type="asset_expiry",
            is_critical=False,
            reminder_date=asset.expiry_date,
            status="pending",
            entity_type="customer_asset",
            entity_id=asset.id,
            source="auto",
        ))
        count += 1
    return count


async def _check_file_expiry_reminders(db: AsyncSession, mode: str, today: date) -> int:
    """Check 4: File index expiry reminders (30 days before)."""
    threshold = today + timedelta(days=30)
    query = select(FileIndex).where(
        FileIndex.expiry_date != None,
        FileIndex.expiry_date <= threshold,
        FileIndex.expiry_date >= today,
        FileIndex.is_current == True,
        FileIndex.is_deleted == False,
    )
    query = _apply_throttle(query, mode)

    result = await db.execute(query)
    files = result.scalars().all()
    count = 0
    for f in files:
        existing = await db.execute(
            select(func.count()).select_from(Reminder).where(
                Reminder.entity_type == "file_index",
                Reminder.entity_id == f.id,
                Reminder.reminder_type == "file_expiry",
                Reminder.is_deleted == False,
            )
        )
        if existing.scalar() > 0:
            continue
        db.add(Reminder(
            title=f"文件到期: {f.name}",
            reminder_type="file_expiry",
            is_critical=False,
            reminder_date=f.expiry_date,
            status="pending",
            entity_type="file_index",
            entity_id=f.id,
            source="auto",
        ))
        count += 1
    return count


async def _check_maintenance_expired(db: AsyncSession, mode: str, today: date) -> int:
    """Check 5: Maintenance periods expired (active -> expired)."""
    query = select(MaintenancePeriod).where(
        MaintenancePeriod.status == "active",
        MaintenancePeriod.end_date < today,
    )
    query = _apply_throttle(query, mode)

    result = await db.execute(query)
    expired_periods = result.scalars().all()
    for mp in expired_periods:
        mp.status = "expired"
        db.add(mp)
    return len(expired_periods)


async def _check_maintenance_near_expiry(db: AsyncSession, mode: str, today: date) -> int:
    """Check 6: Maintenance near-expiry reminders (MAINTENANCE_REMINDER_DAYS_BEFORE days)."""
    threshold = today + timedelta(days=MAINTENANCE_REMINDER_DAYS_BEFORE)
    query = select(MaintenancePeriod).where(
        MaintenancePeriod.status == "active",
        MaintenancePeriod.end_date >= today,
        MaintenancePeriod.end_date <= threshold,
    )
    query = _apply_throttle(query, mode)

    result = await db.execute(query)
    near_periods = result.scalars().all()
    count = 0
    for mp in near_periods:
        existing = await db.execute(
            select(func.count()).select_from(Reminder).where(
                Reminder.entity_type == "maintenance_period",
                Reminder.entity_id == mp.id,
                Reminder.reminder_type == "custom",
                Reminder.is_deleted == False,
            )
        )
        if existing.scalar() > 0:
            continue
        db.add(Reminder(
            title=f"维护期即将到期: {mp.service_description}",
            reminder_type="custom",
            is_critical=False,
            reminder_date=mp.end_date,
            status="pending",
            entity_type="maintenance_period",
            entity_id=mp.id,
            source="auto",
        ))
        count += 1
    return count


async def run_overdue_check(
    db: AsyncSession,
    mode: Literal["full", "throttled"],
) -> dict:
    """
    Run overdue/expiry checks.

    Args:
        mode: "full" for startup (no limits), "throttled" for dashboard (90-day window, 1000 max)

    Returns:
        Dict with processed counts for each check type.
    """
    start_time = time.time()
    source = "启动" if mode == "full" else "仪表盘"
    today = date.today()

    try:
        results = {
            "reminders": await _check_overdue_reminders(db, mode, today),
            "quotations": await _check_expired_quotations(db, mode, today),
            "asset_reminders": await _check_asset_expiry_reminders(db, mode, today),
            "file_reminders": await _check_file_expiry_reminders(db, mode, today),
            "maintenance_expired": await _check_maintenance_expired(db, mode, today),
            "maintenance_reminders": await _check_maintenance_near_expiry(db, mode, today),
        }
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error("逾期检查异常 | source=%s error=%s", source, str(e))
        raise

    elapsed = time.time() - start_time
    logger.info(
        "逾期检查完成 | source=%s reminders=%d quotations=%d asset_reminders=%d file_reminders=%d maintenance_expired=%d maintenance_reminders=%d elapsed=%.3fs",
        source, results["reminders"], results["quotations"],
        results["asset_reminders"], results["file_reminders"],
        results["maintenance_expired"], results["maintenance_reminders"], elapsed,
    )
    return results


async def run_startup_check(db: AsyncSession) -> dict | None:
    """Trigger point A: Full check on startup, once per process lifetime."""
    global _OVERDUE_CHECK_EXECUTED
    if _OVERDUE_CHECK_EXECUTED:
        return None
    _OVERDUE_CHECK_EXECUTED = True
    return await run_overdue_check(db, mode="full")


async def run_dashboard_check(db: AsyncSession) -> dict:
    """Trigger point B: Throttled check on dashboard API call."""
    return await run_overdue_check(db, mode="throttled")
