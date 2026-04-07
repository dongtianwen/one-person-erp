"""FR-504 版本/发布记录 Pydantic schemas——对齐 prd1_5.md 簇 E"""
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import date, datetime


class ReleaseCreate(BaseModel):
    version_no: str
    release_date: date
    release_type: str
    is_current_online: bool = False
    changelog: str
    deploy_env: Optional[str] = None
    notes: Optional[str] = None
    deliverable_id: Optional[int] = None


class ReleaseUpdate(BaseModel):
    version_no: Optional[str] = None
    release_date: Optional[date] = None
    release_type: Optional[str] = None
    is_current_online: Optional[bool] = None
    changelog: Optional[str] = None
    deploy_env: Optional[str] = None
    notes: Optional[str] = None
    deliverable_id: Optional[int] = None


class ReleaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    deliverable_id: Optional[int] = None
    version_no: str
    release_date: date
    release_type: str
    is_current_online: bool
    changelog: str
    deploy_env: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime


class ReleaseListItem(ReleaseResponse):
    """列表项——追加 is_pinned 标记"""
    is_pinned: bool = False
