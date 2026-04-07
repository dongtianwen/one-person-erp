"""FR-501 需求版本管理 Pydantic schemas"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class RequirementCreate(BaseModel):
    version_no: str
    summary: str
    is_current: bool = True
    notes: Optional[str] = None


class RequirementUpdate(BaseModel):
    version_no: Optional[str] = None
    summary: Optional[str] = None
    confirm_status: Optional[str] = None
    confirm_method: Optional[str] = None
    notes: Optional[str] = None


class RequirementResponse(BaseModel):
    id: int
    project_id: int
    version_no: str
    summary: str
    confirm_status: str
    confirmed_at: Optional[datetime] = None
    confirm_method: Optional[str] = None
    is_current: bool
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RequirementListItem(BaseModel):
    """列表项——不含 summary"""
    id: int
    version_no: str
    confirm_status: str
    is_current: bool
    created_at: datetime

    class Config:
        from_attributes = True


class RequirementDetailResponse(RequirementResponse):
    changes: list["RequirementChangeResponse"] = []

    class Config:
        from_attributes = True


# ── 需求变更记录 ──
class RequirementChangeCreate(BaseModel):
    title: str
    description: str
    change_type: str  # add/remove/modify/design
    is_billable: bool = False
    change_order_id: Optional[int] = None
    initiated_by: str


class RequirementChangeResponse(BaseModel):
    id: int
    requirement_id: int
    title: str
    description: str
    change_type: str
    is_billable: bool
    change_order_id: Optional[int] = None
    initiated_by: str
    created_at: datetime

    class Config:
        from_attributes = True
