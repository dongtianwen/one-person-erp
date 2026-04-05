from sqlalchemy import Column, String, Text, ForeignKey, Integer, Float, Date
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class Quotation(Base, TimestampMixin):
    __tablename__ = "quotations"

    quotation_number = Column(String(50), unique=True, nullable=False, index=True)
    title = Column(String(200), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    amount = Column(Float, nullable=False)
    validity_date = Column(Date, nullable=False, index=True)
    status = Column(String(20), default="draft", nullable=False, index=True)
    content = Column(Text, nullable=True)
    discount_note = Column(String(500), nullable=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=True)

    customer = relationship("Customer", back_populates="quotations")
    contract = relationship("Contract")
