from sqlalchemy import Column, String, Text, Integer, Date, ForeignKey, DateTime, Numeric
from sqlalchemy.orm import relationship
from app.models.base import Base


class MaintenancePeriod(Base):
    """售后/维护期记录。"""
    __tablename__ = "maintenance_periods"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False)
    contract_id = Column(Integer, ForeignKey("contracts.id", ondelete="SET NULL"), nullable=True)
    service_type = Column(String(20), nullable=False)
    service_description = Column(String(500), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    annual_fee = Column(Numeric(10, 2), nullable=True)
    status = Column(String(20), nullable=False, default="active")
    renewed_by_id = Column(Integer, ForeignKey("maintenance_periods.id", ondelete="SET NULL"), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: __import__("datetime").datetime.utcnow())

    project = relationship("Project", back_populates="maintenance_periods")
    contract = relationship("Contract")
    renewal = relationship("MaintenancePeriod", remote_side=[id], foreign_keys=[renewed_by_id])
