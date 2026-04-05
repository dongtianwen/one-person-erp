from sqlalchemy import Column, String, Text, ForeignKey, Integer, Date, Float
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class FinanceRecord(Base, TimestampMixin):
    __tablename__ = "finance_records"

    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=True)
    type = Column(String(20), nullable=False)
    amount = Column(Float, nullable=False)
    category = Column(String(50), nullable=True)
    description = Column(Text, default="")
    date = Column(Date, nullable=False)
    invoice_no = Column(String(50), nullable=True, index=True)
    status = Column(String(20), default="pending")

    # v1.1 财务扩展字段
    funding_source = Column(String(30), nullable=True)
    business_note = Column(Text, nullable=True)
    related_record_id = Column(Integer, ForeignKey("finance_records.id"), nullable=True)
    related_note = Column(String(200), nullable=True)

    contract = relationship("Contract", back_populates="finance_records")
    related_record = relationship("FinanceRecord", foreign_keys=[related_record_id], remote_side="FinanceRecord.id")
