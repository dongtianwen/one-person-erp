from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.crud import changelog as changelog_crud
from app.schemas.changelog import ChangeLogResponse

router = APIRouter()


@router.get("", response_model=list[ChangeLogResponse])
async def list_changelogs(
    entity_type: str = Query(...),
    entity_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logs = await changelog_crud.get_changelogs(db, entity_type, entity_id)
    return [ChangeLogResponse.model_validate(log) for log in logs]
