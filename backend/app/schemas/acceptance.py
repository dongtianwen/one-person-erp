"""FR-502 验收管理 Pydantic schemas——对齐 prd1_5.md 簇 C"""
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import date, datetime


class AcceptanceCreate(BaseModel):
    acceptance_name: str
    acceptance_date: date
    acceptor_name: str
    acceptor_title: Optional[str] = None
    result: str  # passed / failed / conditional
    notes: Optional[str] = None
    trigger_payment_reminder: bool = False
    confirm_method: str
    milestone_id: Optional[int] = None


class AcceptanceUpdate(BaseModel):
    acceptance_name: Optional[str] = None
    acceptance_date: Optional[date] = None
    acceptor_name: Optional[str] = None
    acceptor_title: Optional[str] = None
    result: Optional[str] = None
    notes: Optional[str] = None
    trigger_payment_reminder: Optional[bool] = None
    confirm_method: Optional[str] = None
    milestone_id: Optional[int] = None


class AcceptanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    milestone_id: Optional[int] = None
    acceptance_name: str
    acceptance_date: date
    acceptor_name: str
    acceptor_title: Optional[str] = None
    result: str
    notes: Optional[str] = None
    trigger_payment_reminder: bool
    reminder_id: Optional[int] = None
    confirm_method: str
    created_at: datetime


class AppendNotesRequest(BaseModel):
    notes: str
