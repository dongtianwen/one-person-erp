from pydantic import BaseModel
from typing import Optional
from datetime import date


class CustomerAssetBase(BaseModel):
    asset_type: str
    name: str
    expiry_date: Optional[date] = None
    supplier: Optional[str] = None
    annual_fee: Optional[float] = None
    account_info: Optional[str] = None
    notes: Optional[str] = None


class CustomerAssetCreate(CustomerAssetBase):
    pass


class CustomerAssetUpdate(BaseModel):
    asset_type: Optional[str] = None
    name: Optional[str] = None
    expiry_date: Optional[date] = None
    supplier: Optional[str] = None
    annual_fee: Optional[float] = None
    account_info: Optional[str] = None
    notes: Optional[str] = None


class CustomerAssetResponse(CustomerAssetBase):
    id: int
    customer_id: int

    class Config:
        from_attributes = True
