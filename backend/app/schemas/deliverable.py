"""FR-503 交付物管理 Pydantic schemas——对齐 prd1_5.md 簇 D"""
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import date, datetime


class AccountHandoverItem(BaseModel):
    model_config = ConfigDict(extra="allow")  # 允许额外字段以检测密码字段名

    platform_name: str
    account_name: str
    notes: Optional[str] = None


class DeliverableCreate(BaseModel):
    name: str
    deliverable_type: str
    delivery_date: date
    recipient_name: str
    delivery_method: str
    description: Optional[str] = None
    storage_location: Optional[str] = None
    version_no: Optional[str] = None
    acceptance_id: Optional[int] = None
    account_handovers: Optional[list[AccountHandoverItem]] = None


class AccountHandoverResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    platform_name: str
    account_name: str
    notes: Optional[str] = None


class DeliverableResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    acceptance_id: Optional[int] = None
    name: str
    deliverable_type: str
    delivery_date: date
    recipient_name: str
    delivery_method: str
    description: Optional[str] = None
    storage_location: Optional[str] = None
    version_no: Optional[str] = None
    created_at: datetime


class DeliverableDetailResponse(DeliverableResponse):
    account_handovers: list[AccountHandoverResponse] = []
