"""FR-501 需求版本 CRUD"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.models.requirement import Requirement, RequirementChange
from app.schemas.requirement import RequirementCreate, RequirementUpdate, RequirementChangeCreate


class CRUDRequirement(CRUDBase[Requirement, RequirementCreate, RequirementUpdate]):
    async def get_with_changes(self, db: AsyncSession, requirement_id: int) -> Requirement | None:
        result = await db.execute(
            select(Requirement)
            .where(Requirement.id == requirement_id, Requirement.is_deleted == False)
            .options(selectinload(Requirement.changes))
        )
        return result.scalar_one_or_none()

    async def list_by_project(self, db: AsyncSession, project_id: int) -> list[Requirement]:
        result = await db.execute(
            select(Requirement)
            .where(Requirement.project_id == project_id, Requirement.is_deleted == False)
            .order_by(Requirement.created_at.desc())
        )
        return list(result.scalars().all())


class CRUDRequirementChange(CRUDBase[RequirementChange, RequirementChangeCreate, None]):
    pass


requirement = CRUDRequirement(Requirement)
requirement_change = CRUDRequirementChange(RequirementChange)
