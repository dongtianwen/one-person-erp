"""FR-506 售后/维护期管理 API 路由——严格对齐 prd1_5.md 簇 G"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date, timedelta

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.maintenance import MaintenancePeriod
from app.schemas.maintenance import (
    MaintenanceCreate,
    MaintenanceUpdate,
    RenewRequest,
    MaintenanceResponse,
)

logger = logging.getLogger("app.maintenance")
router = APIRouter()

# PATCH 允许修改的白名单
ALLOWED_PATCH_FIELDS = {"service_description", "annual_fee", "notes"}
BLOCKED_STATUSES = {"expired", "renewed", "terminated"}


@router.get("", response_model=list[MaintenanceResponse])
async def list_maintenance_periods(
    project_id: int,
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """返回该项目所有服务期记录，按 end_date 升序。支持 status 筛选"""
    project = await db.get(Project, project_id)
    if not project or project.is_deleted:
        raise HTTPException(status_code=404, detail="项目不存在")

    q = select(MaintenancePeriod).where(MaintenancePeriod.project_id == project_id)
    if status:
        q = q.where(MaintenancePeriod.status == status)
    q = q.order_by(MaintenancePeriod.end_date.asc())

    result = await db.execute(q)
    return list(result.scalars().all())


@router.get("/{period_id}", response_model=MaintenanceResponse)
async def get_maintenance_period(
    project_id: int,
    period_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """返回服务期详情"""
    period = await db.get(MaintenancePeriod, period_id)
    if not period or period.project_id != project_id:
        raise HTTPException(status_code=404, detail="服务期不存在")
    return period


@router.post("", response_model=MaintenanceResponse, status_code=201)
async def create_maintenance_period(
    project_id: int,
    period_in: MaintenanceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建服务期记录。end_date < start_date 返回 422"""
    project = await db.get(Project, project_id)
    if not project or project.is_deleted:
        raise HTTPException(status_code=404, detail="项目不存在")

    if period_in.end_date < period_in.start_date:
        raise HTTPException(status_code=422, detail="结束日期不得早于开始日期")

    period = MaintenancePeriod(
        project_id=project_id,
        contract_id=period_in.contract_id,
        service_type=period_in.service_type,
        service_description=period_in.service_description,
        start_date=period_in.start_date,
        end_date=period_in.end_date,
        annual_fee=period_in.annual_fee,
        notes=period_in.notes,
    )
    db.add(period)
    await db.commit()
    await db.refresh(period)
    return period


@router.post("/{period_id}/renew", response_model=MaintenanceResponse, status_code=201)
async def renew_maintenance_period(
    project_id: int,
    period_id: int,
    renew_in: RenewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """续期操作——三步事务：新记录 + 原记录 status=renewed + renewed_by_id"""
    period = await db.get(MaintenancePeriod, period_id)
    if not period or period.project_id != project_id:
        raise HTTPException(status_code=404, detail="服务期不存在")

    # 新记录 start_date = 原记录 end_date + 1 天（自动计算）
    new_start = period.end_date + timedelta(days=1)
    if renew_in.end_date < new_start:
        raise HTTPException(status_code=422, detail="结束日期不得早于开始日期")

    # 1. 创建新服务期记录
    try:
        new_period = MaintenancePeriod(
            project_id=project_id,
            contract_id=period.contract_id,
            service_type=renew_in.service_type or period.service_type,
            service_description=renew_in.service_description or period.service_description,
            start_date=new_start,
            end_date=renew_in.end_date,
            annual_fee=renew_in.annual_fee if renew_in.annual_fee is not None else period.annual_fee,
        )
        db.add(new_period)
        await db.flush()

        # 2. 原记录 status 变更为 renewed
        period.status = "renewed"
        # 3. 原记录 renewed_by_id 指向新记录 ID
        period.renewed_by_id = new_period.id

        await db.commit()
    except Exception as e:
        logger.error("维护期续期事务失败 | table=maintenance_periods | project_id=%s | original_id=%s | error=%s", project_id, period_id, str(e))
        raise

    await db.refresh(new_period)
    return new_period


@router.patch("/{period_id}", response_model=MaintenanceResponse)
async def patch_maintenance_period(
    project_id: int,
    period_id: int,
    period_in: MaintenanceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """仅允许修改 service_description / annual_fee / notes"""
    period = await db.get(MaintenancePeriod, period_id)
    if not period or period.project_id != project_id:
        raise HTTPException(status_code=404, detail="服务期不存在")

    if period.status in BLOCKED_STATUSES:
        raise HTTPException(status_code=422, detail="已结束的服务期不可修改")

    update_data = period_in.model_dump(exclude_unset=True)
    for field_name in update_data:
        if field_name not in ALLOWED_PATCH_FIELDS:
            raise HTTPException(status_code=422, detail="仅允许修改服务说明、年费和备注")

    for field, value in update_data.items():
        setattr(period, field, value)

    await db.commit()
    await db.refresh(period)
    return period
