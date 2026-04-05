from datetime import date, datetime, timedelta
from sqlalchemy import select, func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.reminder import Reminder, ReminderSetting
from app.schemas.reminder import ReminderCreate, ReminderUpdate, ReminderSettingCreate, ReminderSettingUpdate


class CRUDReminder(CRUDBase[Reminder, ReminderCreate, ReminderUpdate]):

    async def list_with_order(
        self, db: AsyncSession, skip: int = 0, limit: int = 20, filters: dict | None = None
    ) -> tuple[list[Reminder], int]:
        """List reminders with overdue first, then by reminder_date asc."""
        query = select(Reminder).where(Reminder.is_deleted == False)
        count_query = select(func.count()).select_from(Reminder).where(Reminder.is_deleted == False)

        if filters:
            for key, value in filters.items():
                if value is not None:
                    query = query.where(getattr(Reminder, key) == value)
                    count_query = count_query.where(getattr(Reminder, key) == value)

        # Order: overdue first, then pending, then completed. Within same status, by date asc
        status_order = case(
            (Reminder.status == "overdue", 0),
            (Reminder.status == "pending", 1),
            (Reminder.status == "completed", 2),
            else_=3,
        )
        query = query.order_by(status_order, Reminder.reminder_date.asc())

        count_result = await db.execute(count_query)
        total = count_result.scalar()

        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        items = list(result.scalars().all())
        return items, total

    async def check_and_mark_overdue(self, db: AsyncSession) -> int:
        """Mark all pending reminders past their date as overdue. Returns count updated."""
        today = date.today()
        result = await db.execute(
            select(Reminder).where(
                Reminder.status == "pending",
                Reminder.reminder_date < today,
                Reminder.is_deleted == False,
            )
        )
        overdue_items = result.scalars().all()
        for item in overdue_items:
            item.status = "overdue"
        if overdue_items:
            await db.commit()
        return len(overdue_items)

    async def generate_auto_reminder(
        self,
        db: AsyncSession,
        title: str,
        reminder_type: str,
        reminder_date: date,
        entity_type: str | None = None,
        entity_id: int | None = None,
        is_critical: bool = False,
    ) -> Reminder | None:
        """Generate an auto reminder with idempotency protection. Returns None if duplicate."""
        # Check for existing reminder for same entity on same date
        conditions = [
            Reminder.reminder_type == reminder_type,
            Reminder.reminder_date == reminder_date,
            Reminder.is_deleted == False,
        ]
        if entity_type is not None:
            conditions.append(Reminder.entity_type == entity_type)
        else:
            conditions.append(Reminder.entity_type.is_(None))
        if entity_id is not None:
            conditions.append(Reminder.entity_id == entity_id)
        else:
            conditions.append(Reminder.entity_id.is_(None))

        existing = await db.execute(select(Reminder).where(*conditions))
        if existing.scalar_one_or_none():
            return None  # Idempotent: skip duplicate

        reminder = Reminder(
            title=title,
            reminder_type=reminder_type,
            reminder_date=reminder_date,
            is_critical=is_critical,
            status="pending",
            entity_type=entity_type,
            entity_id=entity_id,
            source="auto",
        )
        db.add(reminder)
        await db.flush()
        return reminder

    async def complete(self, db: AsyncSession, reminder_id: int) -> Reminder | None:
        """Mark a reminder as completed."""
        reminder = await self.get(db, reminder_id)
        if not reminder:
            return None
        reminder.status = "completed"
        reminder.completed_at = datetime.utcnow()
        db.add(reminder)
        await db.commit()
        await db.refresh(reminder)
        return reminder

    async def delete_by_entity(self, db: AsyncSession, entity_type: str, entity_id: int) -> None:
        """Soft-delete all auto reminders for a given entity (cascade delete for non-critical)."""
        result = await db.execute(
            select(Reminder).where(
                Reminder.entity_type == entity_type,
                Reminder.entity_id == entity_id,
                Reminder.is_critical == False,
                Reminder.is_deleted == False,
            )
        )
        for r in result.scalars().all():
            r.is_deleted = True
        await db.commit()

    async def get_upcoming(self, db: AsyncSession, days: int = 7, limit: int = 10) -> list[Reminder]:
        """Get overdue + upcoming reminders for dashboard."""
        today = date.today()
        week_later = today + timedelta(days=days)
        result = await db.execute(
            select(Reminder)
            .where(
                Reminder.status.in_(["pending", "overdue"]),
                Reminder.reminder_date <= week_later,
                Reminder.is_deleted == False,
            )
            .order_by(Reminder.reminder_date.asc())
            .limit(limit)
        )
        return list(result.scalars().all())


class CRUDReminderSetting(CRUDBase[ReminderSetting, ReminderSettingCreate, ReminderSettingUpdate]):
    async def get_by_type(self, db: AsyncSession, reminder_type: str) -> ReminderSetting | None:
        result = await db.execute(
            select(ReminderSetting).where(
                ReminderSetting.reminder_type == reminder_type, ReminderSetting.is_deleted == False
            )
        )
        return result.scalar_one_or_none()

    async def get_all_active(self, db: AsyncSession) -> list[ReminderSetting]:
        result = await db.execute(
            select(ReminderSetting).where(ReminderSetting.is_active == True, ReminderSetting.is_deleted == False)
        )
        return list(result.scalars().all())


reminder = CRUDReminder(Reminder)
reminder_setting = CRUDReminderSetting(ReminderSetting)
