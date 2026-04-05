from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.crud.customer_asset import customer_asset as asset_crud
from app.schemas.customer_asset import (
    CustomerAssetCreate, CustomerAssetUpdate, CustomerAssetResponse,
)

router = APIRouter()


@router.get("", response_model=list[CustomerAssetResponse])
async def list_customer_assets(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items = await asset_crud.list_by_customer(db, customer_id)
    return [CustomerAssetResponse.model_validate(a) for a in items]


@router.post("", response_model=CustomerAssetResponse, status_code=201)
async def create_customer_asset(
    customer_id: int,
    asset_in: CustomerAssetCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    obj_dict = asset_in.model_dump()
    obj_dict["customer_id"] = customer_id
    db_obj = asset_crud.model(**obj_dict)
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return CustomerAssetResponse.model_validate(db_obj)


@router.put("/{asset_id}", response_model=CustomerAssetResponse)
async def update_customer_asset(
    customer_id: int,
    asset_id: int,
    asset_in: CustomerAssetUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    asset = await asset_crud.get(db, asset_id)
    if not asset or asset.customer_id != customer_id:
        raise HTTPException(status_code=404, detail="资产记录不存在")
    asset = await asset_crud.update(db, asset, asset_in)
    return CustomerAssetResponse.model_validate(asset)


@router.delete("/{asset_id}")
async def delete_customer_asset(
    customer_id: int,
    asset_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    asset = await asset_crud.get(db, asset_id)
    if not asset or asset.customer_id != customer_id:
        raise HTTPException(status_code=404, detail="资产记录不存在")

    # Sync delete related auto-generated reminders
    from sqlalchemy import delete as sql_delete
    from app.models.reminder import Reminder
    await db.execute(
        sql_delete(Reminder).where(
            Reminder.entity_type == "customer_asset",
            Reminder.entity_id == asset_id,
            Reminder.source == "auto",
        )
    )

    await asset_crud.remove(db, asset_id)
    return {"message": "资产记录已删除"}
