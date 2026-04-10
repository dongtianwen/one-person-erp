from sqlalchemy import Column, String, Text, ForeignKey, Integer, Date, Float, Boolean, Numeric
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class FinanceRecord(Base, TimestampMixin):
    """
    收款记录：实际到账的款项记录，关联合同和发票。
    finance_records.amount 为实收金额，是粗利润计算的收入基准。
    收款记录可关联发票（invoice_id），也可不关联（未开票收款）。
    reconciliation_status 表示该条收款的对账确认状态，由批量同步接口驱动。
    """
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

    # v1.8 财务导出与对账字段
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True)
    accounting_period = Column(String(7), nullable=True)
    export_batch_id = Column(Integer, ForeignKey("export_batches.id", ondelete="SET NULL"), nullable=True)
    reconciliation_status = Column(String(20), nullable=True, default="pending")

    contract = relationship("Contract", back_populates="finance_records")
    related_project = relationship("Project", foreign_keys=[related_project_id])
    related_record = relationship("FinanceRecord", foreign_keys=[related_record_id], remote_side="FinanceRecord.id")
    invoice = relationship("Invoice", foreign_keys=[invoice_id])
