"""FR-505 变更单/增补单 Pydantic schemas——对齐 prd1_5.md 簇 F"""
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from decimal import Decimal


class ChangeOrderCreate(BaseModel):
    title: str
    description: str
    amount: Decimal
    notes: Optional[str] = None
    requirement_change_id: Optional[int] = None


class ChangeOrderUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    amount: Optional[Decimal] = None
    status: Optional[str] = None
    confirm_method: Optional[str] = None
    notes: Optional[str] = None


class ChangeOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_no: str
    contract_id: int
    requirement_change_id: Optional[int] = None
    title: str
    description: str
    amount: Decimal
    status: str
    confirmed_at: Optional[datetime] = None
    confirm_method: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ChangeOrderListResponse(BaseModel):
    items: list[ChangeOrderResponse]
    confirmed_total: Decimal
    actual_receivable: Decimal


class ChangeOrderSummaryItem(BaseModel):
    order_no: str
    title: str
    amount: Decimal
    status: str
    contract_id: int
    contract_no: Optional[str] = None
