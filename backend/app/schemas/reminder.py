from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime


class ReminderBase(BaseModel):
    title: str
    reminder_type: str  # annual_report, tax_filing, contract_expiry, task_deadline, file_expiry, custom
    reminder_date: date
    note: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None


class ReminderCreate(ReminderBase):
    pass


class ReminderUpdate(BaseModel):
    title: Optional[str] = None
    reminder_date: Optional[date] = None
    note: Optional[str] = None


class ReminderResponse(ReminderBase):
    id: int
    is_critical: bool
    status: str
    completed_at: Optional[datetime] = None
    source: str

    class Config:
        from_attributes = True


class ReminderListResponse(BaseModel):
    items: list[ReminderResponse]
    total: int
    page: int
    page_size: int


class ReminderSettingBase(BaseModel):
    reminder_type: str
    config: str  # JSON string
    is_active: bool = True


class ReminderSettingCreate(ReminderSettingBase):
    pass


class ReminderSettingUpdate(BaseModel):
    config: Optional[str] = None
    is_active: Optional[bool] = None


class ReminderSettingResponse(ReminderSettingBase):
    id: int

    class Config:
        from_attributes = True
