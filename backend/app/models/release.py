from sqlalchemy import Column, String, Text, Boolean, Integer, Date, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.models.base import Base


class Release(Base):
    """版本发布记录——只记录 created_at。"""
    __tablename__ = "releases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False)
    deliverable_id = Column(Integer, ForeignKey("deliverables.id", ondelete="SET NULL"), nullable=True)
    version_no = Column(String(50), nullable=False)
    release_date = Column(Date, nullable=False)
    release_type = Column(String(20), nullable=False)
    is_current_online = Column(Boolean, nullable=False, default=False)
    changelog = Column(Text, nullable=False)
    deploy_env = Column(String(20), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: __import__("datetime").datetime.utcnow())

    project = relationship("Project", back_populates="releases")
    deliverable = relationship("Deliverable", back_populates="releases")
