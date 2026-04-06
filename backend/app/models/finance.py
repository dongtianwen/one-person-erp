from sqlalchemy import Column, String, Text, ForeignKey, Integer, Date, Float, Boolean, Numeric
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
    settlement_status = Column(String(20), nullable=True)

    # v1.3 外包协作字段
    outsource_name = Column(String(200), nullable=True)
    has_invoice = Column(Boolean, nullable=True)
    tax_treatment = Column(String(20), nullable=True)

    # v1.3 发票台账字段
    invoice_direction = Column(String(10), nullable=True)
    invoice_type = Column(String(20), nullable=True)
    tax_rate = Column(Numeric(5, 4), nullable=True)
    tax_amount = Column(Numeric(12, 2), nullable=True)

    # v1.4 项目利润核算字段
    related_project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)

    contract = relationship("Contract", back_populates="finance_records")
    related_project = relationship("Project", foreign_keys=[related_project_id])
    related_record = relationship("FinanceRecord", foreign_keys=[related_record_id], remote_side="FinanceRecord.id")
