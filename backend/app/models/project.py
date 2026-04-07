from sqlalchemy import Column, String, Text, ForeignKey, Integer, Date, Float, Boolean
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    name = Column(String(200), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    description = Column(Text, default="")
    status = Column(String(20), default="requirements")
    budget = Column(Float, nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    progress = Column(Integer, default=0)

    customer = relationship("Customer", back_populates="projects")
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    milestones = relationship("Milestone", back_populates="project", cascade="all, delete-orphan")
    contracts = relationship("Contract", back_populates="project", cascade="all, delete-orphan")
    requirements = relationship("Requirement", back_populates="project", cascade="all, delete-orphan")
    acceptances = relationship("Acceptance", back_populates="project")
    deliverables = relationship("Deliverable", back_populates="project")
    releases = relationship("Release", back_populates="project")
    maintenance_periods = relationship("MaintenancePeriod", back_populates="project")


class Task(Base, TimestampMixin):
    __tablename__ = "tasks"

    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, default="")
    assignee = Column(String(100), nullable=True)
    status = Column(String(20), default="todo")
    priority = Column(String(20), default="medium")
    due_date = Column(Date, nullable=True)

    project = relationship("Project", back_populates="tasks")


class Milestone(Base, TimestampMixin):
    __tablename__ = "milestones"

    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, default="")
    due_date = Column(Date, nullable=False)
    completed_date = Column(Date, nullable=True)
    is_completed = Column(Boolean, default=False, nullable=False)

    project = relationship("Project", back_populates="milestones")
