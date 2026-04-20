from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.services.snapshot_service import get_snapshot_history, get_version_diff
from app.core.constants import SNAPSHOT_ENTITY_TYPE_WHITELIST

router = APIRouter()


@router.get("/{entity_type}/{entity_id}/history")
async def snapshot_history(
    entity_type: str,
    entity_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if entity_type not in SNAPSHOT_ENTITY_TYPE_WHITELIST:
        raise HTTPException(status_code=400, detail="INVALID_ENTITY_TYPE")
    history = await get_snapshot_history(db, entity_type, entity_id)
    return history


@router.get("/{entity_type}/{entity_id}/diff")
async def snapshot_diff(
    entity_type: str,
    entity_id: int,
    v1: int = Query(..., description="版本号 A"),
    v2: int = Query(..., description="版本号 B"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if entity_type not in SNAPSHOT_ENTITY_TYPE_WHITELIST:
        raise HTTPException(status_code=400, detail="INVALID_ENTITY_TYPE")
    try:
        diff = await get_version_diff(db, entity_type, entity_id, v1, v2)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return diff
