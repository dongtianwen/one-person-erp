"""v2.2 dashboard_summary 键值聚合模型。"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DashboardSummary(Base):
    __tablename__ = "dashboard_summary"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    metric_key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    metric_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    refreshed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_summary_metric_key", "metric_key", unique=True),
    )
