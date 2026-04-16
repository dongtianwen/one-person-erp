from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import date, datetime


class ContractBase(BaseModel):
    title: str
    customer_id: int
    project_id: Optional[int] = None
    amount: float
    signed_date: Optional[date] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: str = "draft"
    terms: Optional[str] = ""
    expected_payment_date: Optional[date] = None
    payment_stage_note: Optional[str] = None


class ContractCreate(ContractBase):
    pass


class ContractUpdate(BaseModel):
    title: Optional[str] = None
    customer_id: Optional[int] = None
    project_id: Optional[int] = None
    amount: Optional[float] = None
    signed_date: Optional[date] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = None
    terms: Optional[str] = None
    termination_reason: Optional[str] = None
    expected_payment_date: Optional[date] = None
    payment_stage_note: Optional[str] = None


class ContractResponse(ContractBase):
    id: int
    contract_no: str
    quotation_id: Optional[int] = None
    generated_content: Optional[str] = None
    template_id: Optional[int] = None
    content_generated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class ContractListResponse(BaseModel):
    items: list[ContractResponse]
    total: int
    page: int
    page_size: int
