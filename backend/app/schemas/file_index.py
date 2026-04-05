from pydantic import BaseModel
from typing import Optional
from datetime import date


class FileIndexBase(BaseModel):
    file_name: str
    file_type: str
    version: Optional[str] = None
    is_current: bool = True
    issue_date: Optional[date] = None
    expiry_date: Optional[date] = None
    storage_location: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    issuing_authority: Optional[str] = None
    note: Optional[str] = None


class FileIndexCreate(FileIndexBase):
    pass


class FileIndexUpdate(BaseModel):
    file_name: Optional[str] = None
    file_type: Optional[str] = None
    version: Optional[str] = None
    is_current: Optional[bool] = None
    issue_date: Optional[date] = None
    expiry_date: Optional[date] = None
    storage_location: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    issuing_authority: Optional[str] = None
    note: Optional[str] = None


class FileIndexResponse(FileIndexBase):
    id: int

    class Config:
        from_attributes = True


class FileIndexListResponse(BaseModel):
    items: list[FileIndexResponse]
    total: int
    page: int
    page_size: int


class VersionCreate(BaseModel):
    version: Optional[str] = None
    issue_date: Optional[date] = None
    expiry_date: Optional[date] = None
    storage_location: Optional[str] = None
    note: Optional[str] = None
