from sqlalchemy import Column, String, Text, ForeignKey, Integer, Numeric
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class Customer(Base, TimestampMixin):
    """
    客户：合同的签约主体（公司或个人）。
    用于合同、收款、发票、报价单的关联归属。
    一个客户可对应多份合同和多个项目。
    注意：Customer 代表签约法人主体，不是具体联系人。
    """
    __tablename__ = "customers"

    name = Column(String(100), nullable=False, index=True)
    contact_person = Column(String(100), index=True)
    phone = Column(String(20), index=True)
    email = Column(String(100), index=True)
    company = Column(String(200), index=True)
    source = Column(String(50), default="other")
    status = Column(String(20), default="potential")
    notes = Column(Text, default="")
    lost_reason = Column(Text, nullable=True)

    # v1.9 风险展示字段
    overdue_milestone_count = Column(Integer, nullable=False, default=0)
    overdue_amount = Column(Numeric(12, 2), nullable=False, default=0)
    risk_level = Column(String(20), nullable=False, default="normal")

    projects = relationship("Project", back_populates="customer", cascade="all, delete-orphan")
    contracts = relationship("Contract", back_populates="customer", cascade="all, delete-orphan")
    quotations = relationship("Quotation", back_populates="customer", cascade="all, delete-orphan")
    assets = relationship("CustomerAsset", back_populates="customer", cascade="all, delete-orphan")
