from sqlalchemy import Column, String, Text, ForeignKey, Integer, Float, Date
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class CustomerAsset(Base, TimestampMixin):
    __tablename__ = "customer_assets"

    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    asset_type = Column(String(30), nullable=False)
    name = Column(String(200), nullable=False)
    expiry_date = Column(Date, nullable=True, index=True)
    supplier = Column(String(200), nullable=True)
    annual_fee = Column(Float, nullable=True)
    account_info = Column(String(500), nullable=True)
    notes = Column(Text, nullable=True)

    customer = relationship("Customer", back_populates="assets")
