from decimal import Decimal
from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import date


class FinanceRecordBase(BaseModel):
    type: str
    amount: float
    category: Optional[str] = None
    description: str = ""
    date: date
    contract_id: Optional[int] = None
    invoice_no: Optional[str] = None
    status: str = "pending"
    funding_source: Optional[str] = None
    business_note: Optional[str] = None
    related_record_id: Optional[int] = None
    related_note: Optional[str] = None
    settlement_status: Optional[str] = None

    # v1.3 外包协作字段
    outsource_name: Optional[str] = None
    has_invoice: Optional[bool] = None
    tax_treatment: Optional[str] = None

    # v1.3 发票台账字段
    invoice_direction: Optional[str] = None
    invoice_type: Optional[str] = None
    tax_rate: Optional[Decimal] = None
    # tax_amount 不在 Create/Update schema 中——由后端计算


class FinanceRecordCreate(FinanceRecordBase):
    pass


class FinanceRecordUpdate(BaseModel):
    type: Optional[str] = None
    amount: Optional[float] = None
    category: Optional[str] = None
    description: Optional[str] = None
    date: Optional[date] = None
    contract_id: Optional[int] = None
    invoice_no: Optional[str] = None
    status: Optional[str] = None
    funding_source: Optional[str] = None
    business_note: Optional[str] = None
    related_record_id: Optional[int] = None
    related_note: Optional[str] = None
    settlement_status: Optional[str] = None

    # v1.3 外包协作字段
    outsource_name: Optional[str] = None
    has_invoice: Optional[bool] = None
    tax_treatment: Optional[str] = None

    # v1.3 发票台账字段
    invoice_direction: Optional[str] = None
    invoice_type: Optional[str] = None
    tax_rate: Optional[Decimal] = None


class FinanceRecordResponse(BaseModel):
    id: int
    type: str
    amount: float
    category: Optional[str] = None
    description: Optional[str] = None
    date: date
    contract_id: Optional[int] = None
    invoice_no: Optional[str] = None
    status: str = "pending"
    funding_source: Optional[str] = None
    business_note: Optional[str] = None
    related_record_id: Optional[int] = None
    related_note: Optional[str] = None
    settlement_status: Optional[str] = None

    # v1.3 外包协作字段
    outsource_name: Optional[str] = None
    has_invoice: Optional[bool] = None
    tax_treatment: Optional[str] = None

    # v1.3 发票台账字段
    invoice_direction: Optional[str] = None
    invoice_type: Optional[str] = None
    tax_rate: Optional[Decimal] = None
    tax_amount: Optional[Decimal] = None

    class Config:
        from_attributes = True


class FinanceRecordListResponse(BaseModel):
    items: list[FinanceRecordResponse]
    total: int
    page: int
    page_size: int


class MonthlySummary(BaseModel):
    income: float
    expense: float
    profit: float


class CategoryBreakdown(BaseModel):
    categories: dict[str, float]


class DashboardMetrics(BaseModel):
    monthly_income: float
    monthly_expense: float
    monthly_profit: float
    active_projects: int
    customer_conversion_rate: float
    accounts_receivable: float


class FundingSourceBreakdown(BaseModel):
    funding_sources: dict[str, float]
    unclosed_advances: int
    unclosed_loans: int
