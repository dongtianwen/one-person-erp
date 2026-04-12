from sqlalchemy import Column, String, Text, Boolean, Integer, Date, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.models.base import Base


class Acceptance(Base):
    """验收记录——只记录 created_at，不继承 TimestampMixin（无 updated_at）。"""
    __tablename__ = "acceptances"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False)
    milestone_id = Column(Integer, ForeignKey("milestones.id", ondelete="SET NULL"), nullable=True)
    acceptance_name = Column(String(200), nullable=False)
    acceptance_date = Column(Date, nullable=False)
    acceptor_name = Column(String(100), nullable=False)
    acceptor_title = Column(String(100), nullable=True)
    result = Column(String(20), nullable=False)
    notes = Column(Text, nullable=True)
    trigger_payment_reminder = Column(Boolean, nullable=False, default=False)
    reminder_id = Column(Integer, ForeignKey("reminders.id", ondelete="SET NULL"), nullable=True)
    confirm_method = Column(String(20), nullable=False)
    delivery_package_id = Column(
        Integer, ForeignKey("delivery_packages.id", ondelete="RESTRICT"),
        nullable=True, comment="关联交付包ID",
    )
    acceptance_type = Column(String(20), nullable=True, comment="验收类型: dataset/model")
    created_at = Column(DateTime, nullable=False, default=lambda: __import__("datetime").datetime.utcnow())

    project = relationship("Project", back_populates="acceptances")
    milestone = relationship("Milestone")
    deliverables = relationship("Deliverable", back_populates="acceptance")
