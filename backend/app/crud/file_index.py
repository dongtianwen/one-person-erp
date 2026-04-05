from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud.base import CRUDBase
from app.models.file_index import FileIndex
from app.schemas.file_index import FileIndexCreate, FileIndexUpdate


class CRUDFileIndex(CRUDBase[FileIndex, FileIndexCreate, FileIndexUpdate]):
    async def create(self, db: AsyncSession, obj_in: FileIndexCreate) -> FileIndex:
        db_obj = FileIndex(
            file_group_id=obj_in.file_group_id or FileIndex.generate_group_id(),
            file_name=obj_in.file_name,
            file_type=obj_in.file_type,
            version=obj_in.version,
            is_current=obj_in.is_current,
            issue_date=obj_in.issue_date,
            expiry_date=obj_in.expiry_date,
            storage_location=obj_in.storage_location,
            entity_type=obj_in.entity_type,
            entity_id=obj_in.entity_id,
            issuing_authority=obj_in.issuing_authority,
            note=obj_in.note,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def search(
        self,
        db: AsyncSession,
        keyword: str = "",
        file_type: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[FileIndex], int]:
        query = select(FileIndex).where(FileIndex.is_deleted == False)
        count_query = select(func.count()).select_from(FileIndex).where(FileIndex.is_deleted == False)

        if keyword:
            query = query.where(FileIndex.file_name.contains(keyword))
            count_query = count_query.where(FileIndex.file_name.contains(keyword))
        if file_type:
            query = query.where(FileIndex.file_type == file_type)
            count_query = count_query.where(FileIndex.file_type == file_type)

        query = query.order_by(FileIndex.is_current.desc(), FileIndex.created_at.desc())

        count_result = await db.execute(count_query)
        total = count_result.scalar()

        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        items = list(result.scalars().all())
        return items, total

    async def create_version(self, db: AsyncSession, file_id: int, version_data: dict) -> FileIndex | None:
        original = await self.get(db, file_id)
        if not original:
            return None

        result = await db.execute(
            select(FileIndex).where(
                FileIndex.file_group_id == original.file_group_id,
                FileIndex.is_current == True,
                FileIndex.is_deleted == False,
            )
        )
        for old in result.scalars().all():
            old.is_current = False
            db.add(old)

        new_file = FileIndex(
            file_group_id=original.file_group_id,
            file_name=original.file_name,
            file_type=original.file_type,
            is_current=True,
            entity_type=original.entity_type,
            entity_id=original.entity_id,
            issuing_authority=original.issuing_authority,
            **version_data,
        )
        db.add(new_file)
        await db.commit()
        await db.refresh(new_file)
        return new_file

    async def get_versions(self, db: AsyncSession, file_group_id: str) -> list[FileIndex]:
        result = await db.execute(
            select(FileIndex)
            .where(
                FileIndex.file_group_id == file_group_id,
                FileIndex.is_deleted == False,
            )
            .order_by(FileIndex.is_current.desc(), FileIndex.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_group(
        self,
        db: AsyncSession,
        file_group_id: str,
    ) -> list[FileIndex]:
        result = await db.execute(
            select(FileIndex)
            .where(
                FileIndex.file_group_id == file_group_id,
                FileIndex.is_deleted == False,
            )
            .order_by(FileIndex.is_current.desc(), FileIndex.created_at.desc())
        )
        return list(result.scalars().all())


file_index = CRUDFileIndex(FileIndex)
