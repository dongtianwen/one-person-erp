from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime


class ProjectBase(BaseModel):
    name: str
    customer_id: int
    description: str = ""
    status: str = "requirements"
    budget: Optional[float] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    progress: int = 0


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    budget: Optional[float] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    progress: Optional[int] = None
    budget_change_reason: Optional[str] = None


class ProjectResponse(ProjectBase):
    id: int

    class Config:
        from_attributes = True


class TaskBase(BaseModel):
    title: str
    description: str = ""
    assignee: Optional[str] = None
    status: str = "todo"
    priority: str = "medium"
    due_date: Optional[date] = None


class TaskCreate(TaskBase):
    project_id: Optional[int] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assignee: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[date] = None


class TaskResponse(TaskBase):
    id: int
    project_id: int

    class Config:
        from_attributes = True


class MilestoneBase(BaseModel):
    title: str
    description: str = ""
    due_date: date
    is_completed: bool = False
    # v1.7 收款字段
    payment_amount: Optional[float] = None
    payment_due_date: Optional[date] = None


class MilestoneCreate(MilestoneBase):
    project_id: Optional[int] = None


class MilestoneUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[date] = None
    is_completed: Optional[bool] = None
    # v1.7 收款字段
    payment_amount: Optional[float] = None
    payment_due_date: Optional[date] = None


class MilestoneResponse(MilestoneBase):
    id: int
    project_id: int
    completed_date: Optional[date] = None
    # v1.7 收款状态
    payment_status: str = "unpaid"
    payment_received_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ProjectDetailResponse(BaseModel):
    project: ProjectResponse
    tasks: list[TaskResponse]
    milestones: list[MilestoneResponse]
    current_version: Optional[str] = None  # v1.5: 当前线上版本号，无数据时返回 null
