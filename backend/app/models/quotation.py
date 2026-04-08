from sqlalchemy import Column, String, Text, Integer, Numeric, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class Quotation(Base, TimestampMixin):
    __tablename__ = "quotations"

    quote_no = Column(String(30), unique=True, nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(200), nullable=False)
    requirement_summary = Column(Text, nullable=False)
    estimate_days = Column(Integer, nullable=False)
    estimate_hours = Column(Integer, nullable=True)
    daily_rate = Column(Numeric(12, 2), nullable=True)
    direct_cost = Column(Numeric(12, 2), nullable=True)
    risk_buffer_rate = Column(Numeric(5, 2), nullable=False, default=0)
    discount_amount = Column(Numeric(12, 2), nullable=False, default=0)
    tax_rate = Column(Numeric(5, 4), nullable=False, default=0)
    subtotal_amount = Column(Numeric(12, 2), nullable=False, default=0)
    tax_amount = Column(Numeric(12, 2), nullable=False, default=0)
    total_amount = Column(Numeric(12, 2), nullable=False, default=0)
    valid_until = Column(Date, nullable=False, index=True)
    status = Column(String(20), nullable=False, default="draft", index=True)
    notes = Column(Text, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    accepted_at = Column(DateTime, nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    expired_at = Column(DateTime, nullable=True)
    converted_contract_id = Column(Integer, ForeignKey("contracts.id", ondelete="SET NULL"), nullable=True)

    customer = relationship("Customer", back_populates="quotations")
    project = relationship("Project")
    contract = relationship("Contract", foreign_keys=[converted_contract_id])
    items = relationship("QuotationItem", back_populates="quotation", cascade="all, delete-orphan")
    changes = relationship("QuotationChange", back_populates="quotation", cascade="all, delete-orphan")


class QuotationItem(Base):
    __tablename__ = "quotation_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    quotation_id = Column(Integer, ForeignKey("quotations.id", ondelete="CASCADE"), nullable=False)
    item_name = Column(String(200), nullable=False)
    item_type = Column(String(20), nullable=False)
    quantity = Column(Numeric(12, 2), nullable=False, default=1)
    unit_price = Column(Numeric(12, 2), nullable=False, default=0)
    amount = Column(Numeric(12, 2), nullable=False, default=0)
    notes = Column(Text, nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False)

    quotation = relationship("Quotation", back_populates="items")


class QuotationChange(Base):
    __tablename__ = "quotation_changes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    quotation_id = Column(Integer, ForeignKey("quotations.id", ondelete="CASCADE"), nullable=False)
    change_type = Column(String(20), nullable=False)
    before_snapshot = Column(Text, nullable=False)
    after_snapshot = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False)

    quotation = relationship("Quotation", back_populates="changes")
