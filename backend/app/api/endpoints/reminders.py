from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.crud import reminder as reminder_crud
from app.schemas.reminder import (
    ReminderCreate,
    ReminderUpdate,
    ReminderResponse,
    ReminderListResponse,
    ReminderSettingCreate,
    ReminderSettingUpdate,
    ReminderSettingResponse,
)

router = APIRouter()


@router.get("", response_model=ReminderListResponse)
async def list_reminders(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    reminder_type: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    filters = {}
    if reminder_type:
        filters["reminder_type"] = reminder_type
    if status:
        filters["status"] = status
    items, total = await reminder_crud.reminder.list_with_order(db, skip=skip, limit=limit, filters=filters)
    return ReminderListResponse(
        items=[ReminderResponse.model_validate(r) for r in items],
        total=total,
        page=(skip // limit) + 1,
        page_size=limit,
    )


@router.get("/upcoming", response_model=list[ReminderResponse])
async def get_upcoming_reminders(
    days: int = Query(7, ge=1, le=30),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get overdue + upcoming reminders for dashboard widget."""
    items = await reminder_crud.reminder.get_upcoming(db, days=days, limit=limit)
    return [ReminderResponse.model_validate(r) for r in items]


@router.post("", response_model=ReminderResponse, status_code=201)
async def create_reminder(
    reminder_in: ReminderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Only allow custom type for manual creation
    if reminder_in.reminder_type != "custom":
        raise HTTPException(status_code=400, detail="手动创建仅支持自定义类型提醒")
    reminder = await reminder_crud.reminder.create(db, reminder_in)
    return ReminderResponse.model_validate(reminder)


@router.put("/{reminder_id}", response_model=ReminderResponse)
async def update_reminder(
    reminder_id: int,
    reminder_in: ReminderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    reminder = await reminder_crud.reminder.get(db, reminder_id)
    if not reminder:
        raise HTTPException(status_code=404, detail="提醒不存在")
    if reminder.status == "completed":
        raise HTTPException(status_code=400, detail="已完成的提醒不可编辑")
    reminder = await reminder_crud.reminder.update(db, reminder, reminder_in)
    return ReminderResponse.model_validate(reminder)


@router.put("/{reminder_id}/complete", response_model=ReminderResponse)
async def complete_reminder(
    reminder_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    reminder = await reminder_crud.reminder.get(db, reminder_id)
    if not reminder:
        raise HTTPException(status_code=404, detail="提醒不存在")
    if reminder.status == "completed":
        raise HTTPException(status_code=400, detail="提醒已完成")
    result = await reminder_crud.reminder.complete(db, reminder_id)
    return ReminderResponse.model_validate(result)


@router.delete("/{reminder_id}")
async def delete_reminder(
    reminder_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    reminder = await reminder_crud.reminder.get(db, reminder_id)
    if not reminder:
        raise HTTPException(status_code=404, detail="提醒不存在")
    if reminder.is_critical:
        raise HTTPException(status_code=400, detail="关键提醒不可删除")
    await reminder_crud.reminder.remove(db, reminder_id)
    return {"message": "提醒已删除"}


@router.get("/settings", response_model=list[ReminderSettingResponse])
async def get_reminder_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    settings = await reminder_crud.reminder_setting.get_all_active(db)
    return [ReminderSettingResponse.model_validate(s) for s in settings]


@router.put("/settings/{setting_id}", response_model=ReminderSettingResponse)
async def update_reminder_setting(
    setting_id: int,
    setting_in: ReminderSettingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    setting = await reminder_crud.reminder_setting.get(db, setting_id)
    if not setting:
        raise HTTPException(status_code=404, detail="配置不存在")
    setting = await reminder_crud.reminder_setting.update(db, setting, setting_in)
    return ReminderSettingResponse.model_validate(setting)
