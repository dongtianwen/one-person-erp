from decimal import Decimal
from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import date, datetime


class QuotationBase(BaseModel):
    title: str
    customer_id: int
    requirement_summary: str
    estimate_days: int
    project_id: Optional[int] = None
    estimate_hours: Optional[int] = None
    daily_rate: Optional[Decimal] = None
    direct_cost: Optional[Decimal] = None
    risk_buffer_rate: Decimal = Decimal("0")
    discount_amount: Decimal = Decimal("0")
    tax_rate: Decimal = Decimal("0")
    valid_until: date
    notes: Optional[str] = None

    @field_validator("estimate_days")
    @classmethod
    def estimate_days_must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("预计工期必须大于 0")
        return v


class QuotationCreate(QuotationBase):
    pass


class QuotationUpdate(BaseModel):
    title: Optional[str] = None
    customer_id: Optional[int] = None
    requirement_summary: Optional[str] = None
    estimate_days: Optional[int] = None
    project_id: Optional[int] = None
    estimate_hours: Optional[int] = None
    daily_rate: Optional[Decimal] = None
    direct_cost: Optional[Decimal] = None
    risk_buffer_rate: Optional[Decimal] = None
    discount_amount: Optional[Decimal] = None
    tax_rate: Optional[Decimal] = None
    valid_until: Optional[date] = None
    notes: Optional[str] = None
    status: Optional[str] = None

    @field_validator("estimate_days")
    @classmethod
    def estimate_days_must_be_positive(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v <= 0:
            raise ValueError("预计工期必须大于 0")
        return v


class QuotationResponse(BaseModel):
    id: int
    quote_no: str
    customer_id: int
    project_id: Optional[int] = None
    title: str
    requirement_summary: str
    estimate_days: int
    estimate_hours: Optional[int] = None
    daily_rate: Optional[Decimal] = None
    direct_cost: Optional[Decimal] = None
    risk_buffer_rate: Decimal = Decimal("0")
    discount_amount: Decimal = Decimal("0")
    tax_rate: Decimal = Decimal("0")
    subtotal_amount: Decimal = Decimal("0")
    tax_amount: Decimal = Decimal("0")
    total_amount: Decimal = Decimal("0")
    valid_until: date
    status: str
    notes: Optional[str] = None
    template_id: Optional[int] = None
    generated_content: Optional[str] = None
    content_generated_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    accepted_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    expired_at: Optional[datetime] = None
    converted_contract_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class QuotationListResponse(BaseModel):
    items: list[QuotationResponse]
    total: int
    page: int
    page_size: int


class QuotationPreviewRequest(BaseModel):
    """报价预览请求——纯计算不写库。"""
    estimate_days: int
    daily_rate: Optional[Decimal] = None
    direct_cost: Optional[Decimal] = None
    risk_buffer_rate: Decimal = Decimal("0")
    discount_amount: Decimal = Decimal("0")
    tax_rate: Decimal = Decimal("0")

    @field_validator("estimate_days")
    @classmethod
    def estimate_days_must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("预计工期必须大于 0")
        return v


class QuotationPreviewResponse(BaseModel):
    """报价预览响应。"""
    labor_amount: Decimal
    base_amount: Decimal
    buffer_amount: Decimal
    subtotal_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal


class QuotationItemBase(BaseModel):
    item_name: str
    item_type: str
    quantity: Decimal = Decimal("1")
    unit_price: Decimal = Decimal("0")
    notes: Optional[str] = None
    sort_order: int = 0


class QuotationItemCreate(QuotationItemBase):
    pass


class QuotationItemResponse(QuotationItemBase):
    id: int
    quotation_id: int
    amount: Decimal
    created_at: datetime

    class Config:
        from_attributes = True
