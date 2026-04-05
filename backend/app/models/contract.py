from sqlalchemy import Column, String, Text, ForeignKey, Integer, Date, Float
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class Contract(Base, TimestampMixin):
    __tablename__ = "contracts"

    contract_no = Column(String(50), unique=True, nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    title = Column(String(200), nullable=False)
    amount = Column(Float, nullable=False)
    signed_date = Column(Date, nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    status = Column(String(20), default="draft")
    terms = Column(Text, default="")
    termination_reason = Column(Text, nullable=True)

    customer = relationship("Customer", back_populates="contracts")
    project = relationship("Project", back_populates="contracts")
    finance_records = relationship("FinanceRecord", back_populates="contract", cascade="all, delete-orphan")
