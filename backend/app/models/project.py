from sqlalchemy import Column, String, Text, ForeignKey, Integer, Date, Float, Boolean, DateTime, Numeric, JSON
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

    # v1.7 项目关闭和工时字段
    close_checklist = Column(JSON, nullable=True)  # 关闭条件快照
    closed_at = Column(DateTime, nullable=True)  # 关闭时间
    estimated_hours = Column(Integer, nullable=True)  # 预计工时
    actual_hours = Column(Integer, nullable=True)  # 实际工时

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

    # v1.7 收款绑定字段
    payment_amount = Column(Numeric(12, 2), nullable=True)  # 收款金额
    payment_due_date = Column(Date, nullable=True)  # 收款到期日
    payment_received_at = Column(DateTime, nullable=True)  # 实际收款时间
    payment_status = Column(String(20), nullable=False, default="unpaid")  # unpaid/invoiced/received

    project = relationship("Project", back_populates="milestones")
