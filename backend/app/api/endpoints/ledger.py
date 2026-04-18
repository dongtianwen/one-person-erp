"""v2.2 工具入口台账 + 客户线索台账 API 端点。"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.tool_entry import ToolEntry
from app.models.lead import Lead
from app.core.constants import (
    TOOL_ENTRY_STATUS_WHITELIST,
    TOOL_ENTRY_VALID_TRANSITIONS,
    LEAD_SOURCE_WHITELIST,
    LEAD_STATUS_WHITELIST,
    LEAD_VALID_TRANSITIONS,
)
from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)

router = APIRouter()


class ToolEntryCreateRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    action_name: str
    tool_name: str


class ToolEntryStatusUpdateRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    status: str
    is_backfilled: bool | None = None


class LeadCreateRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    source: str = "other"
    status: str = "initial_contact"
    next_action: str | None = None
    client_id: int | None = None
    project_id: int | None = None
    notes: str | None = None


class LeadUpdateRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    source: str | None = None
    status: str | None = None
    next_action: str | None = None
    client_id: int | None = None
    project_id: int | None = None
    notes: str | None = None


# ── 工具入口台账 ──────────────────────────────────────────────────

@router.post("/tool-entries")
async def create_tool_entry(
    req: ToolEntryCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    entry = ToolEntry(action_name=req.action_name, tool_name=req.tool_name, status="pending")
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return {"id": entry.id, "action_name": entry.action_name, "tool_name": entry.tool_name, "status": entry.status}


@router.get("/tool-entries")
async def list_tool_entries(
    status: str | None = None,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(ToolEntry).order_by(ToolEntry.created_at.desc())
    count_query = select(func.count(ToolEntry.id))
    if status:
        query = query.where(ToolEntry.status == status)
        count_query = count_query.where(ToolEntry.status == status)

    total = (await db.execute(count_query)).scalar() or 0
    entries = (await db.execute(query.limit(limit).offset(offset))).scalars().all()
    items = [
        {"id": e.id, "action_name": e.action_name, "tool_name": e.tool_name, "status": e.status, "is_backfilled": e.is_backfilled, "notes": e.notes}
        for e in entries
    ]
    return {"items": items, "total": total}


@router.patch("/tool-entries/{entry_id}/status")
async def update_tool_entry_status(
    entry_id: int,
    req: ToolEntryStatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    entry = (await db.execute(select(ToolEntry).where(ToolEntry.id == entry_id))).scalar_one_or_none()
    if entry is None:
        raise HTTPException(status_code=404, detail="工具入口不存在")

    if req.status not in TOOL_ENTRY_STATUS_WHITELIST:
        raise HTTPException(status_code=400, detail="TOOL_ENTRY_INVALID_TRANSITION")

    valid_next = TOOL_ENTRY_VALID_TRANSITIONS.get(entry.status, [])
    if req.status not in valid_next:
        raise HTTPException(status_code=400, detail="TOOL_ENTRY_INVALID_TRANSITION")

    entry.status = req.status
    if req.is_backfilled is not None:
        entry.is_backfilled = req.is_backfilled
    await db.commit()
    return {"id": entry.id, "status": entry.status, "is_backfilled": entry.is_backfilled}


@router.delete("/tool-entries/{entry_id}")
async def delete_tool_entry(
    entry_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    entry = (await db.execute(select(ToolEntry).where(ToolEntry.id == entry_id))).scalar_one_or_none()
    if entry is None:
        raise HTTPException(status_code=404, detail="工具入口不存在")
    await db.delete(entry)
    await db.commit()
    return {"deleted": True}


# ── 客户线索台账 ──────────────────────────────────────────────────

@router.post("/leads")
async def create_lead(
    req: LeadCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if req.source not in LEAD_SOURCE_WHITELIST:
        raise HTTPException(status_code=400, detail="LEAD_INVALID_TRANSITION")
    if req.status not in LEAD_STATUS_WHITELIST:
        raise HTTPException(status_code=400, detail="LEAD_INVALID_TRANSITION")

    lead = Lead(
        source=req.source, status=req.status, next_action=req.next_action,
        client_id=req.client_id, project_id=req.project_id, notes=req.notes,
    )
    db.add(lead)
    await db.commit()
    await db.refresh(lead)
    return {"id": lead.id, "source": lead.source, "status": lead.status, "next_action": lead.next_action}


@router.get("/leads")
async def list_leads(
    status: str | None = None,
    source: str | None = None,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Lead).order_by(Lead.created_at.desc())
    count_query = select(func.count(Lead.id))
    if status:
        query = query.where(Lead.status == status)
        count_query = count_query.where(Lead.status == status)
    if source:
        query = query.where(Lead.source == source)
        count_query = count_query.where(Lead.source == source)

    total = (await db.execute(count_query)).scalar() or 0
    leads = (await db.execute(query.limit(limit).offset(offset))).scalars().all()
    items = [
        {"id": l.id, "source": l.source, "status": l.status, "next_action": l.next_action, "client_id": l.client_id, "project_id": l.project_id, "notes": l.notes}
        for l in leads
    ]
    return {"items": items, "total": total}


@router.get("/leads/{lead_id}")
async def get_lead(
    lead_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    lead = (await db.execute(select(Lead).where(Lead.id == lead_id))).scalar_one_or_none()
    if lead is None:
        raise HTTPException(status_code=404, detail="线索不存在")
    return {"id": lead.id, "source": lead.source, "status": lead.status, "next_action": lead.next_action, "client_id": lead.client_id, "project_id": lead.project_id, "notes": lead.notes}


@router.put("/leads/{lead_id}")
async def update_lead(
    lead_id: int,
    req: LeadUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    lead = (await db.execute(select(Lead).where(Lead.id == lead_id))).scalar_one_or_none()
    if lead is None:
        raise HTTPException(status_code=404, detail="线索不存在")

    if req.status is not None:
        if req.status not in LEAD_STATUS_WHITELIST:
            raise HTTPException(status_code=400, detail="LEAD_INVALID_TRANSITION")
        valid_next = LEAD_VALID_TRANSITIONS.get(lead.status, [])
        if req.status not in valid_next:
            raise HTTPException(status_code=400, detail="LEAD_INVALID_TRANSITION")
        lead.status = req.status

    if req.source is not None:
        if req.source not in LEAD_SOURCE_WHITELIST:
            raise HTTPException(status_code=400, detail="LEAD_INVALID_TRANSITION")
        lead.source = req.source
    if req.next_action is not None:
        lead.next_action = req.next_action
    if req.client_id is not None:
        lead.client_id = req.client_id
    if req.project_id is not None:
        lead.project_id = req.project_id
    if req.notes is not None:
        lead.notes = req.notes

    await db.commit()
    return {"id": lead.id, "source": lead.source, "status": lead.status, "next_action": lead.next_action, "client_id": lead.client_id}


@router.delete("/leads/{lead_id}")
async def delete_lead(
    lead_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    lead = (await db.execute(select(Lead).where(Lead.id == lead_id))).scalar_one_or_none()
    if lead is None:
        raise HTTPException(status_code=404, detail="线索不存在")
    await db.delete(lead)
    await db.commit()
    return {"deleted": True}
