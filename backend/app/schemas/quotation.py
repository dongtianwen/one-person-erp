from pydantic import BaseModel
from typing import Optional
from datetime import date


class QuotationBase(BaseModel):
    title: str
    customer_id: int
    amount: float
    validity_date: date
    content: Optional[str] = None
    discount_note: Optional[str] = None
    status: str = "draft"


class QuotationCreate(QuotationBase):
    pass


class QuotationUpdate(BaseModel):
    title: Optional[str] = None
    customer_id: Optional[int] = None
    amount: Optional[float] = None
    validity_date: Optional[date] = None
    status: Optional[str] = None
    content: Optional[str] = None
    discount_note: Optional[str] = None


class QuotationResponse(QuotationBase):
    id: int
    quotation_number: str
    contract_id: Optional[int] = None

    class Config:
        from_attributes = True


class QuotationListResponse(BaseModel):
    items: list[QuotationResponse]
    total: int
    page: int
    page_size: int
