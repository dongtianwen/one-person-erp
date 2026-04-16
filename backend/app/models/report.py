from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, ForeignKey, DateTime, Index,
)
from sqlalchemy.orm import relationship

from app.models.base import Base


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_type = Column(String(50), nullable=False)
    entity_id = Column(Integer, nullable=False)
    entity_type = Column(String(20), nullable=False)
    template_id = Column(
        Integer, ForeignKey("templates.id", ondelete="SET NULL"), nullable=True,
    )
    parent_report_id = Column(
        Integer, ForeignKey("reports.id", ondelete="SET NULL"), nullable=True,
    )
    version_no = Column(Integer, nullable=False, default=1)
    is_latest = Column(Integer, nullable=False, default=1)
    content = Column(Text, nullable=True)
    llm_filled_vars = Column(Text, nullable=True)
    llm_provider = Column(String(20), nullable=True)
    llm_model = Column(String(100), nullable=True)
    status = Column(String(20), nullable=False, default="generating")
    error_message = Column(Text, nullable=True)
    generated_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    template = relationship("Template", foreign_keys=[template_id])
    parent_report = relationship("Report", remote_side=[id], foreign_keys=[parent_report_id])

    __table_args__ = (
        Index("idx_reports_entity", "entity_type", "entity_id", created_at.desc()),
        Index("idx_reports_type_status", "report_type", "status"),
    )
