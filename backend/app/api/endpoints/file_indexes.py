from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import timedelta

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.crud import file_index as file_index_crud
from app.schemas.file_index import (
    FileIndexCreate,
    FileIndexUpdate,
    FileIndexResponse,
    FileIndexListResponse,
    VersionCreate,
)

router = APIRouter()


@router.get("", response_model=FileIndexListResponse)
async def list_file_indexes(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = None,
    file_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items, total = await file_index_crud.file_index.search(
        db, keyword=keyword or "", file_type=file_type, skip=skip, limit=limit
    )
    return FileIndexListResponse(
        items=[FileIndexResponse.model_validate(f) for f in items],
        total=total,
        page=(skip // limit) + 1,
        page_size=limit,
    )


@router.post("", response_model=FileIndexResponse, status_code=201)
async def create_file_index(
    file_in: FileIndexCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    file_record = await file_index_crud.file_index.create(db, file_in)

    # Auto-generate expiry reminder if expiry_date is set
    if file_in.expiry_date:
        from app.crud import reminder as reminder_crud

        reminder_date = file_in.expiry_date - timedelta(days=30)
        await reminder_crud.reminder.generate_auto_reminder(
            db,
            title=f"文件即将到期: {file_in.file_name}",
            reminder_type="file_expiry",
            reminder_date=reminder_date,
            entity_type="file_index",
            entity_id=file_record.id,
        )
        await db.commit()

    return FileIndexResponse.model_validate(file_record)


@router.get("/{file_id}", response_model=FileIndexResponse)
async def get_file_index(
    file_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    file_record = await file_index_crud.file_index.get(db, file_id)
    if not file_record:
        raise HTTPException(status_code=404, detail="文件记录不存在")
    return FileIndexResponse.model_validate(file_record)


@router.put("/{file_id}", response_model=FileIndexResponse)
async def update_file_index(
    file_id: int,
    file_in: FileIndexUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    file_record = await file_index_crud.file_index.get(db, file_id)
    if not file_record:
        raise HTTPException(status_code=404, detail="文件记录不存在")
    file_record = await file_index_crud.file_index.update(db, file_record, file_in)
    return FileIndexResponse.model_validate(file_record)


@router.delete("/{file_id}")
async def delete_file_index(
    file_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    file_record = await file_index_crud.file_index.get(db, file_id)
    if not file_record:
        raise HTTPException(status_code=404, detail="文件记录不存在")

    # Delete associated auto reminders
    from app.crud import reminder as reminder_crud

    await reminder_crud.reminder.delete_by_entity(db, "file_index", file_id)

    await file_index_crud.file_index.remove(db, file_id)
    return {"message": "文件记录已删除"}


@router.post("/{file_id}/version", response_model=FileIndexResponse, status_code=201)
async def create_version(
    file_id: int,
    version_in: VersionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    version_data = version_in.model_dump(exclude_unset=True)
    new_version = await file_index_crud.file_index.create_version(db, file_id, version_data)
    if not new_version:
        raise HTTPException(status_code=404, detail="文件记录不存在")

    # Auto-generate expiry reminder for new version if applicable
    if new_version.expiry_date:
        from app.crud import reminder as reminder_crud

        reminder_date = new_version.expiry_date - timedelta(days=30)
        await reminder_crud.reminder.generate_auto_reminder(
            db,
            title=f"文件即将到期: {new_version.file_name}",
            reminder_type="file_expiry",
            reminder_date=reminder_date,
            entity_type="file_index",
            entity_id=new_version.id,
        )
        await db.commit()

    return FileIndexResponse.model_validate(new_version)


@router.get("/{file_id}/versions", response_model=list[FileIndexResponse])
async def get_versions(
    file_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    file_record = await file_index_crud.file_index.get(db, file_id)
    if not file_record:
        raise HTTPException(status_code=404, detail="文件记录不存在")
    versions = await file_index_crud.file_index.get_versions(db, file_record.file_name, file_record.file_type)
    return [FileIndexResponse.model_validate(v) for v in versions]
