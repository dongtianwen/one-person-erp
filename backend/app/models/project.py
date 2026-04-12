from datetime import datetime
from sqlalchemy import Column, String, Text, ForeignKey, Integer, Date, Float, Boolean, DateTime, Numeric, JSON
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class Project(Base, TimestampMixin):
    """
    项目：合同的执行单元，用于跟踪交付进度和工时成本。
    通常一份合同对应一个项目。
    项目是里程碑、工时记录、变更单、验收、交付物的归属容器。
    项目粗利润 = 实收金额 - 工时成本 - 固定成本 - 进项成本。
    """
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

    # v1.9 粗利润缓存
    cached_revenue = Column(Numeric(12, 2), nullable=True)
    cached_labor_cost = Column(Numeric(12, 2), nullable=True)
    cached_fixed_cost = Column(Numeric(12, 2), nullable=True)
    cached_input_cost = Column(Numeric(12, 2), nullable=True)
    cached_gross_profit = Column(Numeric(12, 2), nullable=True)
    cached_gross_margin = Column(Numeric(8, 4), nullable=True)
    profit_cache_updated_at = Column(DateTime, nullable=True)

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


class WorkHourLog(Base):
    """v1.7 工时记录表。"""

    __tablename__ = "work_hour_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, comment="所属项目ID")
    log_date = Column(DateTime, nullable=False, comment="记录日期")
    hours_spent = Column(Numeric(6, 2), nullable=False, comment="工时数")
    task_description = Column(Text, nullable=False, comment="任务描述")
    deviation_note = Column(Text, nullable=True, comment="偏差说明")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")


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
