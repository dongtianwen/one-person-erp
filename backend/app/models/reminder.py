from sqlalchemy import Column, String, Text, Boolean, Integer, Date, DateTime
from app.models.base import Base, TimestampMixin


class Reminder(Base, TimestampMixin):
    __tablename__ = "reminders"

    title = Column(String(200), nullable=False)
    reminder_type = Column(String(30), nullable=False)  # annual_report, tax_filing, contract_expiry, task_deadline, file_expiry, custom
    is_critical = Column(Boolean, default=False, nullable=False)
    reminder_date = Column(Date, nullable=False)
    status = Column(String(20), default="pending", nullable=False)  # pending, overdue, completed
    entity_type = Column(String(30), nullable=True)  # contract, task, file_index
    entity_id = Column(Integer, nullable=True)
    note = Column(Text, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    source = Column(String(20), default="manual", nullable=False)  # manual, auto


class ReminderSetting(Base, TimestampMixin):
    __tablename__ = "reminder_settings"

    reminder_type = Column(String(30), nullable=False, unique=True)
    config = Column(Text, nullable=False)  # JSON string with period, day, etc.
    is_active = Column(Boolean, default=True, nullable=False)
