"""v2.2 leads 客户线索台账模型。"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="other")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="initial_contact")
    next_action: Mapped[str | None] = mapped_column(String(500), nullable=True)
    client_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)
    project_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
