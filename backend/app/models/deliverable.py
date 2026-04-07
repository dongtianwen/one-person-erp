from sqlalchemy import Column, String, Text, Integer, Date, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.models.base import Base


class Deliverable(Base):
    """交付物记录——只记录 created_at。"""
    __tablename__ = "deliverables"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False)
    acceptance_id = Column(Integer, ForeignKey("acceptances.id", ondelete="SET NULL"), nullable=True)
    name = Column(String(200), nullable=False)
    deliverable_type = Column(String(30), nullable=False)
    delivery_date = Column(Date, nullable=False)
    recipient_name = Column(String(100), nullable=False)
    delivery_method = Column(String(20), nullable=False)
    description = Column(Text, nullable=True)
    storage_location = Column(String(500), nullable=True)
    version_no = Column(String(50), nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: __import__("datetime").datetime.utcnow())

    project = relationship("Project", back_populates="deliverables")
    acceptance = relationship("Acceptance", back_populates="deliverables")
    account_handovers = relationship("AccountHandover", back_populates="deliverable", cascade="all, delete-orphan")
    releases = relationship("Release", back_populates="deliverable")


class AccountHandover(Base):
    """账号交接条目。"""
    __tablename__ = "account_handovers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    deliverable_id = Column(Integer, ForeignKey("deliverables.id", ondelete="CASCADE"), nullable=False)
    platform_name = Column(String(200), nullable=False)
    account_name = Column(String(200), nullable=False)
    notes = Column(String(500), nullable=True)

    deliverable = relationship("Deliverable", back_populates="account_handovers")
