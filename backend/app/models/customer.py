from sqlalchemy import Column, String, Text, ForeignKey, Integer
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class Customer(Base, TimestampMixin):
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

    projects = relationship("Project", back_populates="customer", cascade="all, delete-orphan")
    contracts = relationship("Contract", back_populates="customer", cascade="all, delete-orphan")
