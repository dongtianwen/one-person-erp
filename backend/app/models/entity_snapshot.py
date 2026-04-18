"""v2.2 entity_snapshots 统一快照模型。"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class EntitySnapshot(Base):
    __tablename__ = "entity_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    snapshot_json: Mapped[str] = mapped_column(Text, nullable=False)
    parent_snapshot_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_latest: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_snapshots_entity", "entity_type", "entity_id", "created_at"),
        Index("idx_snapshots_latest", "entity_type", "entity_id", "is_latest"),
    )
