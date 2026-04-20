from pydantic import BaseModel, EmailStr
from typing import Optional


class CustomerBase(BaseModel):
    name: str
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None
    source: Optional[str] = "other"
    status: Optional[str] = "potential"
    notes: Optional[str] = ""
    lost_reason: Optional[str] = None


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None
    source: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    lost_reason: Optional[str] = None


class CustomerResponse(CustomerBase):
    id: int
    overdue_milestone_count: int = 0
    overdue_amount: float = 0
    risk_level: str = "normal"

    class Config:
        from_attributes = True


class CustomerDetailResponse(BaseModel):
    customer: CustomerResponse
    projects: list[dict] = []
    contracts: list[dict] = []
    lifetime_value: Optional[dict] = None


class CustomerListResponse(BaseModel):
    items: list[CustomerResponse]
    total: int
    page: int
    page_size: int
