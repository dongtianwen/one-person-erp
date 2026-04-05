from typing import Any, Dict, Generic, List, Optional, Type, TypeVar
from fastapi import HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model

    async def get(self, db: AsyncSession, id: int) -> Optional[ModelType]:
        result = await db.execute(select(self.model).where(self.model.id == id, self.model.is_deleted == False))
        return result.scalar_one_or_none()

    async def list(
        self, db: AsyncSession, skip: int = 0, limit: int = 20, filters: Optional[Dict[str, Any]] = None
    ) -> tuple[List[ModelType], int]:
        query = select(self.model).where(self.model.is_deleted == False)
        count_query = select(func.count()).select_from(self.model).where(self.model.is_deleted == False)

        if filters:
            for key, value in filters.items():
                if value is not None:
                    query = query.where(getattr(self.model, key) == value)
                    count_query = count_query.where(getattr(self.model, key) == value)

        count_result = await db.execute(count_query)
        total = count_result.scalar()

        query = query.offset(skip).limit(limit).order_by(self.model.created_at.desc())
        result = await db.execute(query)
        items = result.scalars().all()
        return list(items), total

    async def create(self, db: AsyncSession, obj_in: CreateSchemaType) -> ModelType:
        obj_dict = obj_in.model_dump()
        db_obj = self.model(**obj_dict)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(self, db: AsyncSession, db_obj: ModelType, obj_in: UpdateSchemaType) -> ModelType:
        obj_data = db_obj.__dict__
        update_data = obj_in.model_dump(exclude_unset=True)
        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def remove(self, db: AsyncSession, id: int) -> bool:
        obj = await self.get(db, id)
        if obj is None:
            return False
        obj.is_deleted = True
        db.add(obj)
        await db.commit()
        return True
