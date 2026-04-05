from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud.base import CRUDBase
from app.models.file_index import FileIndex
from app.schemas.file_index import FileIndexCreate, FileIndexUpdate


class CRUDFileIndex(CRUDBase[FileIndex, FileIndexCreate, FileIndexUpdate]):

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

        # Show current versions first, then by created_at desc
        query = query.order_by(FileIndex.is_current.desc(), FileIndex.created_at.desc())

        count_result = await db.execute(count_query)
        total = count_result.scalar()

        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        items = list(result.scalars().all())
        return items, total

    async def create_version(self, db: AsyncSession, file_id: int, version_data: dict) -> FileIndex | None:
        """Create a new version of an existing file. Demotes old current version."""
        original = await self.get(db, file_id)
        if not original:
            return None

        # Demote old current versions in the same group
        result = await db.execute(
            select(FileIndex).where(
                FileIndex.file_name == original.file_name,
                FileIndex.file_type == original.file_type,
                FileIndex.is_current == True,
                FileIndex.is_deleted == False,
            )
        )
        for old in result.scalars().all():
            old.is_current = False
            db.add(old)

        # Create new version
        new_file = FileIndex(
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

    async def get_versions(self, db: AsyncSession, file_name: str, file_type: str) -> list[FileIndex]:
        """Get all versions of a file grouped by name+type."""
        result = await db.execute(
            select(FileIndex).where(
                FileIndex.file_name == file_name,
                FileIndex.file_type == file_type,
                FileIndex.is_deleted == False,
            ).order_by(FileIndex.is_current.desc(), FileIndex.created_at.desc())
        )
        return list(result.scalars().all())


file_index = CRUDFileIndex(FileIndex)
