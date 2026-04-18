"""v2.2 会议纪要 API 端点。"""

import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.meeting_minute import MeetingMinute
from app.services.snapshot_service import create_snapshot
from app.core.constants import WARNING_SNAPSHOT_WRITE_FAILED
from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)

router = APIRouter()


class MinutesCreateRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    title: str
    participants: str | None = None
    conclusions: str | None = None
    action_items: str | None = None
    risk_points: str | None = None
    project_id: int | None = None
    client_id: int | None = None
    meeting_date: str | None = None


class MinutesUpdateRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    title: str | None = None
    participants: str | None = None
    conclusions: str | None = None
    action_items: str | None = None
    risk_points: str | None = None
    project_id: int | None = None
    client_id: int | None = None
    meeting_date: str | None = None


def _minutes_to_dict(m: MeetingMinute) -> dict:
    return {
        "id": m.id,
        "title": m.title,
        "participants": m.participants,
        "conclusions": m.conclusions,
        "action_items": m.action_items,
        "risk_points": m.risk_points,
        "project_id": m.project_id,
        "client_id": m.client_id,
        "meeting_date": m.meeting_date.isoformat() if m.meeting_date else None,
        "created_at": m.created_at.isoformat() if m.created_at else None,
        "updated_at": m.updated_at.isoformat() if m.updated_at else None,
    }


@router.post("")
async def create_minutes(
    req: MinutesCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if req.project_id is None and req.client_id is None:
        raise HTTPException(status_code=400, detail="MINUTES_ASSOCIATION_REQUIRED")

    minutes = MeetingMinute(
        title=req.title,
        participants=req.participants,
        conclusions=req.conclusions,
        action_items=req.action_items,
        risk_points=req.risk_points,
        project_id=req.project_id,
        client_id=req.client_id,
        meeting_date=datetime.fromisoformat(req.meeting_date) if req.meeting_date else None,
    )
    db.add(minutes)
    await db.commit()
    await db.refresh(minutes)

    warning_code = None
    success, warning = await create_snapshot(
        db=db,
        entity_type="minutes",
        entity_id=minutes.id,
        snapshot_json={
            "title": minutes.title,
            "participants": minutes.participants,
            "conclusions": minutes.conclusions,
            "action_items": minutes.action_items,
            "risk_points": minutes.risk_points,
        },
    )
    if not success:
        warning_code = warning

    result = _minutes_to_dict(minutes)
    if warning_code:
        result["warning_code"] = warning_code
    return result


@router.get("")
async def list_minutes(
    project_id: int | None = None,
    client_id: int | None = None,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(MeetingMinute).order_by(MeetingMinute.created_at.desc())
    count_query = select(func.count(MeetingMinute.id))

    if project_id is not None:
        query = query.where(MeetingMinute.project_id == project_id)
        count_query = count_query.where(MeetingMinute.project_id == project_id)
    if client_id is not None:
        query = query.where(MeetingMinute.client_id == client_id)
        count_query = count_query.where(MeetingMinute.client_id == client_id)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    result = await db.execute(query.limit(limit).offset(offset))
    minutes_list = result.scalars().all()

    items = [_minutes_to_dict(m) for m in minutes_list]
    return {"items": items, "total": total}


@router.get("/{minutes_id}")
async def get_minutes(
    minutes_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(MeetingMinute).where(MeetingMinute.id == minutes_id))
    minutes = result.scalar_one_or_none()
    if minutes is None:
        raise HTTPException(status_code=404, detail="纪要不存在")
    return _minutes_to_dict(minutes)


@router.put("/{minutes_id}")
async def update_minutes(
    minutes_id: int,
    req: MinutesUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(MeetingMinute).where(MeetingMinute.id == minutes_id))
    minutes = result.scalar_one_or_none()
    if minutes is None:
        raise HTTPException(status_code=404, detail="纪要不存在")

    if req.project_id is None and req.client_id is None:
        if minutes.project_id is None and minutes.client_id is None:
            raise HTTPException(status_code=400, detail="MINUTES_ASSOCIATION_REQUIRED")

    if req.title is not None:
        minutes.title = req.title
    if req.participants is not None:
        minutes.participants = req.participants
    if req.conclusions is not None:
        minutes.conclusions = req.conclusions
    if req.action_items is not None:
        minutes.action_items = req.action_items
    if req.risk_points is not None:
        minutes.risk_points = req.risk_points
    if req.project_id is not None:
        minutes.project_id = req.project_id
    if req.client_id is not None:
        minutes.client_id = req.client_id
    if req.meeting_date is not None:
        minutes.meeting_date = datetime.fromisoformat(req.meeting_date)

    await db.commit()
    await db.refresh(minutes)

    warning_code = None
    success, warning = await create_snapshot(
        db=db,
        entity_type="minutes",
        entity_id=minutes.id,
        snapshot_json={
            "title": minutes.title,
            "participants": minutes.participants,
            "conclusions": minutes.conclusions,
            "action_items": minutes.action_items,
            "risk_points": minutes.risk_points,
        },
    )
    if not success:
        warning_code = warning

    result_data = _minutes_to_dict(minutes)
    if warning_code:
        result_data["warning_code"] = warning_code
    return result_data


@router.delete("/{minutes_id}")
async def delete_minutes(
    minutes_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(MeetingMinute).where(MeetingMinute.id == minutes_id))
    minutes = result.scalar_one_or_none()
    if minutes is None:
        raise HTTPException(status_code=404, detail="纪要不存在")
    await db.delete(minutes)
    await db.commit()
    return {"deleted": True}
