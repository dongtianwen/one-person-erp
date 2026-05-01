from decimal import Decimal
from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import date, datetime

from app.core.constants import (
    RD_CATEGORY_WHITELIST,
    RD_STATUS_WHITELIST,
    RD_SUB_TO_CATEGORY_MAP,
)


class RdExpenseBase(BaseModel):
    rd_category: str
    rd_sub_category: Optional[str] = None
    amount: float
    tax_amount: Optional[float] = 0
    expense_date: date
    project_id: Optional[int] = None
    finance_record_id: Optional[int] = None
    contract_id: Optional[int] = None
    description: str = ""
    vendor_name: Optional[str] = None
    invoice_no: Optional[str] = None
    has_invoice: Optional[bool] = None
    invoice_type: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("rd_category")
    @classmethod
    def validate_rd_category(cls, v: str) -> str:
        if v not in RD_CATEGORY_WHITELIST:
            raise ValueError(f"rd_category must be one of {RD_CATEGORY_WHITELIST}")
        return v

    @field_validator("rd_sub_category")
    @classmethod
    def validate_rd_sub_category(cls, v: Optional[str], info) -> Optional[str]:
        if v is None:
            return v
        if v not in RD_SUB_TO_CATEGORY_MAP:
            raise ValueError(f"Invalid rd_sub_category: {v}")
        return v

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("amount must be positive")
        return v


class RdExpenseCreate(RdExpenseBase):
    pass


class RdExpenseUpdate(BaseModel):
    rd_category: Optional[str] = None
    rd_sub_category: Optional[str] = None
    amount: Optional[float] = None
    tax_amount: Optional[float] = None
    expense_date: Optional[date] = None
    project_id: Optional[int] = None
    finance_record_id: Optional[int] = None
    contract_id: Optional[int] = None
    description: Optional[str] = None
    vendor_name: Optional[str] = None
    invoice_no: Optional[str] = None
    has_invoice: Optional[bool] = None
    invoice_type: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("rd_category")
    @classmethod
    def validate_rd_category(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in RD_CATEGORY_WHITELIST:
            raise ValueError(f"rd_category must be one of {RD_CATEGORY_WHITELIST}")
        return v

    @field_validator("rd_sub_category")
    @classmethod
    def validate_rd_sub_category(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in RD_SUB_TO_CATEGORY_MAP:
            raise ValueError(f"Invalid rd_sub_category: {v}")
        return v

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v <= 0:
            raise ValueError("amount must be positive")
        return v


class RdExpenseResponse(BaseModel):
    id: int
    rd_no: str
    rd_category: str
    rd_sub_category: Optional[str] = None
    amount: float
    tax_amount: Optional[float] = 0
    total_amount: Optional[float] = None
    expense_date: date
    accounting_period: Optional[str] = None
    project_id: Optional[int] = None
    finance_record_id: Optional[int] = None
    contract_id: Optional[int] = None
    description: Optional[str] = None
    vendor_name: Optional[str] = None
    invoice_no: Optional[str] = None
    has_invoice: Optional[bool] = None
    invoice_type: Optional[str] = None
    status: str
    notes: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = {"from_attributes": True}

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def convert_datetime(cls, v: Optional[datetime]) -> Optional[str]:
        if v is None:
            return None
        if isinstance(v, datetime):
            return v.isoformat()
        return v


class RdExpenseListResponse(BaseModel):
    items: list[RdExpenseResponse]
    total: int


class RdCategorySummaryItem(BaseModel):
    category: str
    category_label: str
    amount: float
    tax_amount: float
    total_amount: float
    count: int


class RdSummaryResponse(BaseModel):
    period: str
    total_amount: float
    total_tax_amount: float
    total_grand: float
    categories: list[RdCategorySummaryItem]


class RdStatusUpdateRequest(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in RD_STATUS_WHITELIST:
            raise ValueError(f"status must be one of {RD_STATUS_WHITELIST}")
        return v
