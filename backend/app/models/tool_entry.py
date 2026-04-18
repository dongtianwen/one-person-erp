"""v2.2 tool_entries 工具入口台账模型。"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ToolEntry(Base):
    __tablename__ = "tool_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    action_name: Mapped[str] = mapped_column(String(200), nullable=False)
    tool_name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    is_backfilled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
