"""v2.2 meeting_minutes 会议纪要模型。"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class MeetingMinute(Base):
    __tablename__ = "meeting_minutes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    participants: Mapped[str | None] = mapped_column(Text, nullable=True)
    conclusions: Mapped[str | None] = mapped_column(Text, nullable=True)
    action_items: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_points: Mapped[str | None] = mapped_column(Text, nullable=True)
    project_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    client_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)
    meeting_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
