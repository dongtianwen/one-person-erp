import logging
import time
from datetime import date, timedelta
from typing import Literal

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reminder import Reminder
from app.models.file_index import FileIndex
from app.models.quotation import Quotation
from app.models.customer_asset import CustomerAsset

logger = logging.getLogger("app.overdue_check")

_OVERDUE_CHECK_EXECUTED = False


def _reset_check_flag() -> None:
    """Reset the startup check flag (for testing only)."""
    global _OVERDUE_CHECK_EXECUTED
    _OVERDUE_CHECK_EXECUTED = False


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
    results = {"reminders": 0, "quotations": 0, "asset_reminders": 0, "file_reminders": 0}

    try:
        # --- Check 1: Overdue reminders (pending → overdue) ---
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
        results["reminders"] = len(overdue_reminders)

        # --- Check 2: Expired quotations (draft/sent → expired) ---
        q_query = select(Quotation).where(
            Quotation.status.in_(["draft", "sent"]),
            Quotation.validity_date < today,
            Quotation.is_deleted == False,
        )
        if mode == "throttled":
            q_query = q_query.limit(1000)

        q_result = await db.execute(q_query)
        expired_quotations = q_result.scalars().all()
        for q in expired_quotations:
            q.status = "expired"
            db.add(q)
        results["quotations"] = len(expired_quotations)

        # --- Check 3: Asset expiry reminders (30 days before) ---
        asset_threshold = today + timedelta(days=30)
        a_query = select(CustomerAsset).where(
            CustomerAsset.expiry_date != None,
            CustomerAsset.expiry_date <= asset_threshold,
            CustomerAsset.expiry_date >= today,
            CustomerAsset.is_deleted == False,
        )
        if mode == "throttled":
            a_query = a_query.limit(1000)

        a_result = await db.execute(a_query)
        assets = a_result.scalars().all()
        for asset in assets:
            # Idempotent check: skip if reminder already exists
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

            reminder = Reminder(
                title=f"客户资产到期: {asset.name}",
                reminder_type="asset_expiry",
                is_critical=False,
                reminder_date=asset.expiry_date,
                status="pending",
                entity_type="customer_asset",
                entity_id=asset.id,
                source="auto",
            )
            db.add(reminder)
            results["asset_reminders"] += 1

        # --- Check 4: File index expiry reminders (30 days before) ---
        f_query = select(FileIndex).where(
            FileIndex.expiry_date != None,
            FileIndex.expiry_date <= asset_threshold,
            FileIndex.expiry_date >= today,
            FileIndex.is_current == True,
            FileIndex.is_deleted == False,
        )
        if mode == "throttled":
            f_query = f_query.limit(1000)

        f_result = await db.execute(f_query)
        files = f_result.scalars().all()
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

            reminder = Reminder(
                title=f"文件到期: {f.name}",
                reminder_type="file_expiry",
                is_critical=False,
                reminder_date=f.expiry_date,
                status="pending",
                entity_type="file_index",
                entity_id=f.id,
                source="auto",
            )
            db.add(reminder)
            results["file_reminders"] += 1

        await db.commit()

    except Exception as e:
        await db.rollback()
        logger.error("逾期检查异常 | source=%s error=%s", source, str(e))
        raise

    elapsed = time.time() - start_time
    total = sum(results.values())
    logger.info(
        "逾期检查完成 | source=%s reminders=%d quotations=%d asset_reminders=%d file_reminders=%d elapsed=%.3fs",
        source, results["reminders"], results["quotations"],
        results["asset_reminders"], results["file_reminders"], elapsed,
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
