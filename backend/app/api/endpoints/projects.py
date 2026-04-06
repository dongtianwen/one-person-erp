from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import date

from app.core.profit_utils import calculate_project_profit

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.crud import project as project_crud
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectDetailResponse,
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    MilestoneCreate,
    MilestoneUpdate,
    MilestoneResponse,
)

router = APIRouter()


@router.get("")
async def list_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    customer_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    filters = {}
    if status:
        filters["status"] = status
    if customer_id:
        filters["customer_id"] = customer_id
    items, _ = await project_crud.project.list(db, skip=skip, limit=limit, filters=filters)

    result = []
    for p in items:
        proj_dict = ProjectResponse.model_validate(p).model_dump()
        profit_data = await calculate_project_profit(p.id, db)
        proj_dict["profit"] = float(profit_data["profit"])
        proj_dict["profit_margin"] = float(profit_data["profit_margin"]) if profit_data["profit_margin"] is not None else None
        result.append(proj_dict)
    return result


@router.get("/{project_id}", response_model=ProjectDetailResponse)
async def get_project(
    project_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    project = await project_crud.project.get_with_relations(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return ProjectDetailResponse(
        project=ProjectResponse.model_validate(project),
        tasks=[TaskResponse.model_validate(t) for t in project.tasks],
        milestones=[MilestoneResponse.model_validate(m) for m in project.milestones],
    )


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    project_in: ProjectCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    if project_in.start_date and project_in.end_date and project_in.start_date > project_in.end_date:
        raise HTTPException(status_code=400, detail="开始日期不能晚于结束日期")
    project = await project_crud.project.create(db, project_in)
    return ProjectResponse.model_validate(project)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    project_in: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = await project_crud.project.get(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    if project_in.budget is not None and project.budget != project_in.budget:
        if not project_in.budget_change_reason:
            raise HTTPException(status_code=400, detail="预算变更必须记录原因")

    # Record budget change log before update
    if project_in.budget is not None and project.budget != project_in.budget:
        from app.crud import changelog as changelog_crud
        await changelog_crud.create_changelog(
            db, "project", project.id, "budget",
            str(project.budget), str(project_in.budget),
            changed_by=current_user.id,
        )

    project = await project_crud.project.update(db, project, project_in)
    return ProjectResponse.model_validate(project)


@router.get("/{project_id}/profit")
async def get_project_profit(
    project_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """FR-401: 项目利润核算接口"""
    project = await project_crud.project.get(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    result = await calculate_project_profit(project_id, db)
    return {
        "project_id": project.id,
        "project_name": project.name,
        "income": float(result["income"]),
        "cost": float(result["cost"]),
        "profit": float(result["profit"]),
        "profit_margin": float(result["profit_margin"]) if result["profit_margin"] is not None else None,
        "currency": "CNY",
    }


@router.delete("/{project_id}")
async def delete_project(
    project_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    project = await project_crud.project.get(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    await project_crud.project.remove(db, project_id)
    return {"message": "项目已删除"}


@router.get("/{project_id}/tasks", response_model=list[TaskResponse])
async def list_tasks(
    project_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    project = await project_crud.project.get_with_relations(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return [TaskResponse.model_validate(t) for t in project.tasks]


@router.post("/{project_id}/tasks", response_model=TaskResponse, status_code=201)
async def create_task(
    project_id: int,
    task_in: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task_in.project_id = project_id
    task = await project_crud.task.create(db, task_in)
    return TaskResponse.model_validate(task)


@router.put("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_in: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = await project_crud.task.get(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    task = await project_crud.task.update(db, task, task_in)
    return TaskResponse.model_validate(task)


@router.get("/{project_id}/milestones", response_model=list[MilestoneResponse])
async def list_milestones(
    project_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    project = await project_crud.project.get_with_relations(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return [MilestoneResponse.model_validate(m) for m in project.milestones]


@router.post("/{project_id}/milestones", response_model=MilestoneResponse, status_code=201)
async def create_milestone(
    project_id: int,
    milestone_in: MilestoneCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    milestone_in.project_id = project_id
    milestone = await project_crud.milestone.create(db, milestone_in)
    project = await project_crud.project.get(db, project_id)
    if project:
        await project_crud.project.update_progress(db, project)
    return MilestoneResponse.model_validate(milestone)


@router.put("/milestones/{milestone_id}", response_model=MilestoneResponse)
async def update_milestone(
    milestone_id: int,
    milestone_in: MilestoneUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    milestone = await project_crud.milestone.get(db, milestone_id)
    if not milestone:
        raise HTTPException(status_code=404, detail="里程碑不存在")

    if milestone_in.is_completed and not milestone.is_completed:
        milestone = await project_crud.milestone.complete(db, milestone)
    else:
        milestone = await project_crud.milestone.update(db, milestone, milestone_in)

    # Re-fetch project with relations to update progress
    project = await project_crud.project.get(db, milestone.project_id)
    if project:
        await project_crud.project.update_progress(db, project)
    return MilestoneResponse.model_validate(milestone)
