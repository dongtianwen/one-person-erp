"""FR-506 售后/维护期管理 Pydantic schemas——对齐 prd1_5.md 簇 G"""
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import date, datetime
from decimal import Decimal


class MaintenanceCreate(BaseModel):
    service_type: str
    service_description: str
    start_date: date
    end_date: date
    annual_fee: Optional[Decimal] = None
    contract_id: Optional[int] = None
    notes: Optional[str] = None


class MaintenanceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")  # 拒绝白名单外的字段

    service_description: Optional[str] = None
    annual_fee: Optional[Decimal] = None
    notes: Optional[str] = None


class RenewRequest(BaseModel):
    end_date: date
    service_type: Optional[str] = None
    service_description: Optional[str] = None
    annual_fee: Optional[Decimal] = None


class MaintenanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    contract_id: Optional[int] = None
    service_type: str
    service_description: str
    start_date: date
    end_date: date
    annual_fee: Optional[Decimal] = None
    status: str
    renewed_by_id: Optional[int] = None
    notes: Optional[str] = None
    created_at: datetime
