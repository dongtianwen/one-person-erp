from datetime import datetime
from pydantic import BaseModel
from typing import Optional


class ChangeLogResponse(BaseModel):
    id: int
    entity_type: str
    entity_id: int
    field: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    changed_by: Optional[int] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
