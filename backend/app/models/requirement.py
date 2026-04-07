from sqlalchemy import Column, String, Text, Boolean, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class Requirement(Base, TimestampMixin):
    __tablename__ = "requirements"

    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    version_no = Column(String(50), nullable=False)
    summary = Column(Text, nullable=False)
    confirm_status = Column(String(20), nullable=False, default="pending")
    confirmed_at = Column(DateTime, nullable=True)
    confirm_method = Column(String(20), nullable=True)
    is_current = Column(Boolean, nullable=False, default=False)
    notes = Column(Text, nullable=True)

    project = relationship("Project", back_populates="requirements")
    changes = relationship("RequirementChange", back_populates="requirement", cascade="all, delete-orphan")


class RequirementChange(Base):
    """需求变更记录——不继承 TimestampMixin，只有 created_at。"""
    __tablename__ = "requirement_changes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    requirement_id = Column(Integer, ForeignKey("requirements.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    change_type = Column(String(20), nullable=False)
    is_billable = Column(Boolean, nullable=False, default=False)
    change_order_id = Column(Integer, ForeignKey("change_orders.id", ondelete="SET NULL"), nullable=True)
    initiated_by = Column(String(20), nullable=False)
    created_at = Column(DateTime, nullable=False, default=lambda: __import__("datetime").datetime.utcnow())

    requirement = relationship("Requirement", back_populates="changes")
    change_order = relationship("ChangeOrder", back_populates="requirement_changes")
