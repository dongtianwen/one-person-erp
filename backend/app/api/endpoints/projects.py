import sqlite3
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import date, datetime
from pydantic import BaseModel

from app.core.profit_utils import calculate_project_profit
from app.core.milestone_payment_utils import (
    validate_payment_transition_sync,
    get_project_payment_summary,
    get_overdue_payment_milestones,
)
from app.core.project_close_utils import (
    check_project_close_conditions,
    close_project_sync,
)
from app.core.work_hour_utils import (
    get_work_hour_summary,
    validate_work_hour_log,
    check_deviation_exceeds_threshold,
)

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.crud import project as project_crud
from app.core.exception_handlers import BusinessException
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
    # v1.5: 查询当前线上版本
    from app.models.release import Release as ReleaseModel
    release_result = await db.execute(
        select(ReleaseModel).where(
            ReleaseModel.project_id == project_id,
            ReleaseModel.is_current_online == True,
        )
    )
    current_release = release_result.scalar_one_or_none()
    current_version = current_release.version_no if current_release else None

    return ProjectDetailResponse(
        project=ProjectResponse.model_validate(project),
        tasks=[TaskResponse.model_validate(t) for t in project.tasks],
        milestones=[MilestoneResponse.model_validate(m) for m in project.milestones],
        current_version=current_version,
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


# ── v1.7 里程碑收款绑定接口 ──────────────────────────────────────────


@router.patch("/milestones/{milestone_id}/payment-invoiced", response_model=MilestoneResponse)
async def mark_milestone_invoiced(
    milestone_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """标记里程碑为已开票（invoiced）。要求里程碑已完成。"""
    milestone = await project_crud.milestone.get(db, milestone_id)
    if not milestone:
        raise HTTPException(status_code=404, detail="里程碑不存在")

    # 使用同步连接校验状态流转
    sync_db = sqlite3.connect("shubiao.db")
    try:
        validation = validate_payment_transition_sync(sync_db, milestone_id, "invoiced")
        if not validation["allowed"]:
            if "已完成" in validation["reason"]:
                raise BusinessException(status_code=409, detail=validation["reason"], code="MILESTONE_NOT_COMPLETED")
            raise HTTPException(status_code=409, detail=validation["reason"])
    finally:
        sync_db.close()

    # 更新状态
    from sqlalchemy import update as sa_update
    await db.execute(
        sa_update(project_crud.milestone.model)
        .where(project_crud.milestone.model.id == milestone_id)
        .values(payment_status="invoiced")
    )
    await db.commit()

    # 刷新并返回
    await db.refresh(milestone)
    return MilestoneResponse.model_validate(milestone)


@router.patch("/milestones/{milestone_id}/payment-received", response_model=MilestoneResponse)
async def mark_milestone_payment_received(
    milestone_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """标记里程碑收款已到账（received）。终态。"""
    milestone = await project_crud.milestone.get(db, milestone_id)
    if not milestone:
        raise HTTPException(status_code=404, detail="里程碑不存在")

    # 使用同步连接校验状态流转
    sync_db = sqlite3.connect("shubiao.db")
    try:
        validation = validate_payment_transition_sync(sync_db, milestone_id, "received")
        if not validation["allowed"]:
            raise HTTPException(status_code=409, detail=validation["reason"])
    finally:
        sync_db.close()

    # 更新状态和收款时间
    from sqlalchemy import update as sa_update
    await db.execute(
        sa_update(project_crud.milestone.model)
        .where(project_crud.milestone.model.id == milestone_id)
        .values(
            payment_status="received",
            payment_received_at=datetime.utcnow(),
        )
    )
    await db.commit()

    # 刷新并返回
    await db.refresh(milestone)
    return MilestoneResponse.model_validate(milestone)


@router.get("/{project_id}/payment-summary")
async def get_payment_summary(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取项目收款汇总，包含逾期未收款里程碑列表。"""
    project = await project_crud.project.get(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 使用同步连接获取汇总数据
    sync_db = sqlite3.connect("shubiao.db")
    try:
        summary = get_project_payment_summary(sync_db, project_id)
        overdue = get_overdue_payment_milestones(sync_db, project_id)
    finally:
        sync_db.close()

    return {
        **summary,
        "overdue_milestones": overdue,
    }


# ── v1.7 项目关闭接口 ───────────────────────────────────────────────


@router.get("/{project_id}/close-check")
async def check_close_conditions(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """检查项目是否满足关闭条件。只读接口。"""
    project = await project_crud.project.get(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 使用同步连接检查条件
    sync_db = sqlite3.connect("shubiao.db")
    try:
        conditions = check_project_close_conditions(sync_db, project_id)
    finally:
        sync_db.close()

    return conditions


@router.post("/{project_id}/close")
async def close_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """关闭项目。必须满足所有关闭条件。"""
    project = await project_crud.project.get(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 使用同步连接执行关闭
    sync_db = sqlite3.connect("shubiao.db")
    try:
        result = close_project_sync(sync_db, project_id)
    finally:
        sync_db.close()

    if not result["success"]:
        # 判断错误类型
        if "已关闭" in result["message"]:
            raise BusinessException(status_code=409, detail=result["message"], code="PROJECT_ALREADY_CLOSED")
        elif "不满足关闭条件" in result["message"]:
            raise BusinessException(
                status_code=409,
                detail="项目关闭条件未满足",
                code="PROJECT_CLOSE_CONDITIONS_NOT_MET",
            )
        else:
            raise HTTPException(status_code=400, detail=result["message"])

    # 刷新项目数据
    await db.refresh(project)
    return {
        "message": "项目已关闭",
        "project_id": project_id,
        "closed_at": result.get("closed_at"),
    }


# ── v1.7 工时记录接口 ───────────────────────────────────────────────


class WorkHourLogCreate(BaseModel):
    """工时记录创建请求。"""
    log_date: date
    hours_spent: float
    task_description: str
    deviation_note: Optional[str] = None


class WorkHourLogResponse(BaseModel):
    """工时记录响应。"""
    id: int
    project_id: int
    log_date: date
    hours_spent: float
    task_description: str
    deviation_note: Optional[str] = None
    created_at: datetime


class EstimatedHoursUpdate(BaseModel):
    """预计工时更新请求。"""
    estimated_hours: int


@router.post("/{project_id}/work-hours", response_model=WorkHourLogResponse, status_code=201)
async def create_work_hour_log(
    project_id: int,
    log_in: WorkHourLogCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建工时记录。"""
    project = await project_crud.project.get(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 使用同步连接获取当前偏差状态
    sync_db = sqlite3.connect("shubiao.db")
    try:
        summary = get_work_hour_summary(sync_db, project_id)
        # 计算添加新记录后的总工时
        new_actual_hours = summary["actual_hours_total"] + log_in.hours_spent
        deviation_info = validate_work_hour_log(
            log_in.hours_spent,
            check_deviation_exceeds_threshold(project.estimated_hours, new_actual_hours),
            log_in.deviation_note,
        )
    finally:
        sync_db.close()

    if not deviation_info["allowed"]:
        raise HTTPException(status_code=422, detail=deviation_info["reason"])

    # 创建工时记录
    from sqlalchemy import insert
    sync_db = sqlite3.connect("shubiao.db")
    try:
        cur = sync_db.cursor()
        cur.execute("""
            INSERT INTO work_hour_logs (project_id, log_date, hours_spent, task_description, deviation_note, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (project_id, log_in.log_date.isoformat(), log_in.hours_spent, log_in.task_description, log_in.deviation_note, datetime.utcnow().isoformat()))
        sync_db.commit()
        log_id = cur.lastrowid
    finally:
        sync_db.close()

    # 获取创建的记录
    sync_db = sqlite3.connect("shubiao.db")
    try:
        cur = sync_db.cursor()
        cur.execute("SELECT * FROM work_hour_logs WHERE id = ?", (log_id,))
        row = cur.fetchone()
    finally:
        sync_db.close()

    return WorkHourLogResponse(
        id=row[0],
        project_id=row[1],
        log_date=datetime.fromisoformat(row[2]).date() if isinstance(row[2], str) else row[2],
        hours_spent=float(row[3]),
        task_description=row[4],
        deviation_note=row[5],
        created_at=datetime.fromisoformat(row[7]) if isinstance(row[7], str) else row[7],
    )


@router.get("/{project_id}/work-hours")
async def list_work_hours(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取项目工时记录列表。"""
    project = await project_crud.project.get(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 使用同步连接获取工时汇总
    sync_db = sqlite3.connect("shubiao.db")
    try:
        summary = get_work_hour_summary(sync_db, project_id)
    finally:
        sync_db.close()

    return summary


@router.get("/{project_id}/work-hours/summary")
async def get_work_hours_summary(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取项目工时汇总统计。"""
    project = await project_crud.project.get(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 使用同步连接获取工时汇总
    sync_db = sqlite3.connect("shubiao.db")
    try:
        summary = get_work_hour_summary(sync_db, project_id)
    finally:
        sync_db.close()

    return {
        "estimated_hours": summary["estimated_hours"],
        "actual_hours_total": summary["actual_hours_total"],
        "deviation_rate": summary["deviation_rate"],
        "deviation_exceeds_threshold": summary["deviation_exceeds_threshold"],
    }


@router.patch("/{project_id}/estimated-hours")
async def update_estimated_hours(
    project_id: int,
    update_in: EstimatedHoursUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新项目预计工时。"""
    project = await project_crud.project.get(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    if update_in.estimated_hours < 0:
        raise HTTPException(status_code=422, detail="预计工时不能为负数")

    # 更新预计工时
    from sqlalchemy import update as sa_update
    await db.execute(
        sa_update(project_crud.project.model)
        .where(project_crud.project.model.id == project_id)
        .values(estimated_hours=update_in.estimated_hours)
    )
    await db.commit()

    return {"estimated_hours": update_in.estimated_hours}
