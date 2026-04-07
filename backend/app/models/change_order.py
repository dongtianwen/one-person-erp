from sqlalchemy import Column, String, Text, Integer, ForeignKey, DateTime, Numeric
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class ChangeOrder(Base, TimestampMixin):
    __tablename__ = "change_orders"

    order_no = Column(String(30), unique=True, nullable=False)
    contract_id = Column(Integer, ForeignKey("contracts.id", ondelete="RESTRICT"), nullable=False)
    requirement_change_id = Column(Integer, nullable=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    status = Column(String(20), nullable=False, default="draft")
    confirmed_at = Column(DateTime, nullable=True)
    confirm_method = Column(String(20), nullable=True)
    notes = Column(Text, nullable=True)

    contract = relationship("Contract", back_populates="change_orders")
    requirement_changes = relationship("RequirementChange", back_populates="change_order")
