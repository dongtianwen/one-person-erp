from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.crud.base import CRUDBase
from app.models.project import Project, Task, Milestone
from app.schemas.project import ProjectCreate, ProjectUpdate, TaskCreate, TaskUpdate, MilestoneCreate, MilestoneUpdate


class CRUDProject(CRUDBase[Project, ProjectCreate, ProjectUpdate]):
    async def get_with_relations(self, db: AsyncSession, id: int) -> Project | None:
        result = await db.execute(
            select(Project)
            .where(Project.id == id, Project.is_deleted == False)
            .options(selectinload(Project.tasks), selectinload(Project.milestones))
        )
        return result.scalar_one_or_none()

    async def update_progress(self, db: AsyncSession, project: Project) -> Project:
        milestone_result = await db.execute(
            select(Milestone).where(Milestone.project_id == project.id, Milestone.is_deleted == False)
        )
        milestones = milestone_result.scalars().all()
        if milestones:
            completed = sum(1 for m in milestones if m.is_completed)
            project.progress = int((completed / len(milestones)) * 100)
            db.add(project)
            await db.commit()
            await db.refresh(project)
        return project


class CRUDTask(CRUDBase[Task, TaskCreate, TaskUpdate]):
    pass


class CRUDMilestone(CRUDBase[Milestone, MilestoneCreate, MilestoneUpdate]):
    async def complete(self, db: AsyncSession, milestone: Milestone) -> Milestone:
        from datetime import date

        milestone.is_completed = True
        milestone.completed_date = date.today()
        db.add(milestone)
        await db.commit()
        await db.refresh(milestone)
        return milestone


project = CRUDProject(Project)
task = CRUDTask(Task)
milestone = CRUDMilestone(Milestone)
