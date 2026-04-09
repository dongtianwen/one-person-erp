"""v1.8 财务导出 Schema——API 请求和响应模型。"""

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class ExportRequest(BaseModel):
    """创建导出批次请求。"""
    export_type: str = Field(..., description="导出类型: contracts, payments, invoices")
    target_format: str = Field(default="generic", description="目标格式")
    accounting_period: Optional[str] = Field(None, description="会计期间 YYYY-MM")
    start_date: Optional[date] = Field(None, description="开始日期")
    end_date: Optional[date] = Field(None, description="结束日期")

    @field_validator("export_type")
    @classmethod
    def validate_export_type(cls, v: str) -> str:
        valid_types = ["contracts", "payments", "invoices"]
        if v not in valid_types:
            raise ValueError(f"导出类型必须是以下之一: {', '.join(valid_types)}")
        return v

    @field_validator("target_format")
    @classmethod
    def validate_target_format(cls, v: str) -> str:
        from app.core.constants import EXPORT_FORMAT_SUPPORTED
        if v not in EXPORT_FORMAT_SUPPORTED:
            raise ValueError(f"目标格式必须是以下之一: {', '.join(EXPORT_FORMAT_SUPPORTED)}")
        return v


class ExportBatchResponse(BaseModel):
    """导出批次响应。"""
    id: int
    batch_id: str
    export_type: str
    target_format: str
    accounting_period: Optional[str] = None
    start_date: date
    end_date: date
    record_count: int
    file_path: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ExportBatchListResponse(BaseModel):
    """导出批次列表响应。"""
    items: list[ExportBatchResponse]
    total: int
    page: int
    page_size: int


class ExportCreateResponse(BaseModel):
    """创建导出响应。"""
    id: int
    batch_id: str
    file_path: str
    record_count: int
