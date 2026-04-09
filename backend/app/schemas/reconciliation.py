"""v1.8 会计期间对账 Schema——API 请求和响应模型。"""

from datetime import date
from typing import Optional
from pydantic import BaseModel


class OpeningBalance(BaseModel):
    """期初余额。"""
    accounts_receivable: float
    unbilled_amount: float
    total: float


class CurrentPeriodActivity(BaseModel):
    """本期活动统计。"""
    contracts_signed: int
    contracts_amount: float
    invoices_issued: int
    invoices_amount: float
    payments_received: int
    payments_amount: float
    invoices_verified: int
    verified_amount: float


class ClosingBalance(BaseModel):
    """期末余额。"""
    accounts_receivable: float
    unbilled_amount: float
    total: float


class CustomerBreakdownItem(BaseModel):
    """客户维度分解。"""
    customer_id: int
    customer_name: str
    contracts_amount_this_period: float
    invoices_amount_this_period: float
    payments_amount_this_period: float
    outstanding_balance: float


class UnreconciledRecord(BaseModel):
    """未对账记录。"""
    record_id: int
    record_type: str
    amount: float
    transaction_date: str
    reason: str


class ReconciliationReport(BaseModel):
    """对账报表。"""
    accounting_period: str
    period_start: str
    period_end: str
    opening_balance: OpeningBalance
    current_period: CurrentPeriodActivity
    closing_balance: ClosingBalance
    breakdown: list[CustomerBreakdownItem]
    unreconciled_records: list[UnreconciledRecord]


class SyncRequest(BaseModel):
    """同步对账状态请求。"""
    record_ids: list[int]


class SyncResponse(BaseModel):
    """同步响应。"""
    updated_count: int


class PeriodListResponse(BaseModel):
    """期间列表响应。"""
    periods: list[str]
