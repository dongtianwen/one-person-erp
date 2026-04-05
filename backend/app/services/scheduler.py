"""Scheduled tasks for reminder management."""
import json
import logging
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.crud import reminder as reminder_crud
from app.models.reminder import Reminder, ReminderSetting
from app.models.contract import Contract
from app.models.project import Task

logger = logging.getLogger(__name__)


async def run_daily_tasks() -> None:
    """Run all daily scheduled tasks."""
    async with async_session() as db:
        # 1. Mark overdue reminders
        count = await reminder_crud.reminder.check_and_mark_overdue(db)
        if count:
            logger.info("Marked %d reminders as overdue", count)

        # 2. Generate contract expiry reminders (7 days before)
        await _generate_contract_reminders(db)

        # 3. Generate task deadline reminders (3 days before)
        await _generate_task_reminders(db)

        # 4. Generate periodic reminders (annual report, tax filing)
        await _generate_periodic_reminders(db)

        # 5. Generate file expiry reminders (30 days before)
        await _generate_file_reminders(db)


async def _generate_contract_reminders(db: AsyncSession) -> None:
    """Generate reminders for contracts expiring in 7 days."""
    today = date.today()
    target_date = today + timedelta(days=7)
    result = await db.execute(
        select(Contract).where(
            Contract.end_date == target_date,
            Contract.status.in_(["active", "executing"]),
            Contract.is_deleted == False,
        )
    )
    for contract in result.scalars().all():
        await reminder_crud.reminder.generate_auto_reminder(
            db,
            title=f"合同即将到期: {contract.title}",
            reminder_type="contract_expiry",
            reminder_date=target_date,
            entity_type="contract",
            entity_id=contract.id,
        )
    await db.commit()


async def _generate_task_reminders(db: AsyncSession) -> None:
    """Generate reminders for tasks due in 3 days."""
    today = date.today()
    target_date = today + timedelta(days=3)
    result = await db.execute(
        select(Task).where(
            Task.due_date == target_date,
            Task.status.in_(["todo", "in_progress"]),
            Task.is_deleted == False,
        )
    )
    for task in result.scalars().all():
        await reminder_crud.reminder.generate_auto_reminder(
            db,
            title=f"任务即将截止: {task.title}",
            reminder_type="task_deadline",
            reminder_date=target_date,
            entity_type="task",
            entity_id=task.id,
        )
    await db.commit()


async def _generate_file_reminders(db: AsyncSession) -> None:
    """Generate file expiry reminders 30 days before."""
    today = date.today()
    target_date = today + timedelta(days=30)
    try:
        from app.models.file_index import FileIndex

        result = await db.execute(
            select(FileIndex).where(
                FileIndex.expiry_date == target_date,
                FileIndex.is_current == True,
                FileIndex.is_deleted == False,
            )
        )
        for f in result.scalars().all():
            await reminder_crud.reminder.generate_auto_reminder(
                db,
                title=f"文件即将到期: {f.file_name}",
                reminder_type="file_expiry",
                reminder_date=target_date,
                entity_type="file_index",
                entity_id=f.id,
            )
        await db.commit()
    except Exception:
        pass  # FileIndex table may not exist yet


async def _generate_periodic_reminders(db: AsyncSession) -> None:
    """Generate annual report and tax filing reminders based on settings."""
    settings = await reminder_crud.reminder_setting.get_all_active(db)
    today = date.today()

    for setting in settings:
        try:
            config = json.loads(setting.config)
        except (json.JSONDecodeError, TypeError):
            continue

        if setting.reminder_type == "annual_report":
            month = config.get("month", 3)
            day = config.get("day", 31)
            # Clamp day to valid range for the month
            import calendar

            max_day = calendar.monthrange(today.year, month)[1]
            day = min(day, max_day)
            target_date = date(today.year, month, day)
            if target_date < today:
                max_day = calendar.monthrange(today.year + 1, month)[1]
                day = min(config.get("day", 31), max_day)
                target_date = date(today.year + 1, month, day)
            await reminder_crud.reminder.generate_auto_reminder(
                db,
                title="年报/审计提醒",
                reminder_type="annual_report",
                reminder_date=target_date,
                is_critical=True,
            )

        elif setting.reminder_type == "tax_filing":
            day = config.get("day", 15)
            if today.day == 1:  # Generate on 1st of each month for the filing day
                import calendar as cal

                max_day = cal.monthrange(today.year, today.month)[1]
                filing_day = min(day, max_day)
                target_date = date(today.year, today.month, filing_day)
                await reminder_crud.reminder.generate_auto_reminder(
                    db,
                    title=f"税期申报提醒 ({today.year}-{today.month:02d})",
                    reminder_type="tax_filing",
                    reminder_date=target_date,
                    is_critical=True,
                )

    await db.commit()


def setup_scheduler(app) -> None:
    """Setup APScheduler for daily tasks."""
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.cron import CronTrigger

        scheduler = AsyncIOScheduler()
        scheduler.add_job(
            run_daily_tasks,
            CronTrigger(hour=0, minute=5),
            id="daily_reminder_tasks",
            name="Daily Reminder Tasks",
            replace_existing=True,
        )
        # Also run once on startup (for dev testing)
        scheduler.add_job(
            run_daily_tasks,
            id="startup_reminder_tasks",
            name="Startup Reminder Tasks",
            replace_existing=True,
        )
        scheduler.start()
        logger.info("APScheduler started for reminder tasks")
    except ImportError:
        logger.warning("APScheduler not installed, scheduled tasks disabled")
    except Exception:
        logger.exception("Failed to setup scheduler")
