"""v1.8 发票台账 Schema——API 请求和响应模型。"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class InvoiceBase(BaseModel):
    """发票基础字段。"""
    contract_id: int = Field(..., description="关联合同ID")
    invoice_type: str = Field(default="standard", description="发票类型")
    invoice_date: date = Field(..., description="发票日期")
    amount_excluding_tax: Decimal = Field(..., gt=0, description="不含税金额")
    tax_rate: Optional[Decimal] = Field(default=Decimal("0.13"), ge=0, le=1, description="税率")
    notes: Optional[str] = Field(None, description="备注")

    @field_validator("invoice_type")
    @classmethod
    def validate_invoice_type(cls, v: str) -> str:
        from app.core.constants import INVOICE_TYPE_WHITELIST
        if v not in INVOICE_TYPE_WHITELIST:
            raise ValueError(f"发票类型必须是以下之一: {', '.join(INVOICE_TYPE_WHITELIST)}")
        return v


class InvoiceCreate(InvoiceBase):
    """创建发票请求。"""
    pass


class InvoiceUpdate(BaseModel):
    """更新发票请求（部分更新）。"""
    invoice_type: Optional[str] = None
    invoice_date: Optional[date] = None
    amount_excluding_tax: Optional[Decimal] = None
    tax_rate: Optional[Decimal] = None
    notes: Optional[str] = None

    @field_validator("invoice_type")
    @classmethod
    def validate_invoice_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            from app.core.constants import INVOICE_TYPE_WHITELIST
            if v not in INVOICE_TYPE_WHITELIST:
                raise ValueError(f"发票类型必须是以下之一: {', '.join(INVOICE_TYPE_WHITELIST)}")
        return v


class InvoiceStatusUpdate(BaseModel):
    """状态更新请求（用于状态流转）。"""
    received_by: Optional[str] = Field(None, description="收票人")


class InvoiceResponse(InvoiceBase):
    """发票响应。"""
    id: int
    invoice_no: str
    tax_amount: Decimal
    total_amount: Decimal
    status: str
    issued_at: Optional[datetime] = None
    received_at: Optional[datetime] = None
    received_by: Optional[str] = None
    verified_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class InvoiceListResponse(BaseModel):
    """发票列表响应。"""
    items: list[InvoiceResponse]
    total: int
    page: int
    page_size: int


class InvoiceSummary(BaseModel):
    """单状态汇总。"""
    count: int
    total_amount: Decimal


class InvoiceSummaryResponse(BaseModel):
    """发票汇总响应。"""
    draft: InvoiceSummary
    issued: InvoiceSummary
    received: InvoiceSummary
    verified: InvoiceSummary
    cancelled: InvoiceSummary


class InvoiceContractResponse(BaseModel):
    """合同关联发票响应。"""
    id: int
    invoice_no: str
    invoice_type: str
    invoice_date: date
    amount_excluding_tax: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    status: str

    class Config:
        from_attributes = True
