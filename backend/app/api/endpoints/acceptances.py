"""FR-502 验收管理 API 路由——严格对齐 prd1_5.md 簇 C"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.acceptance import Acceptance
from app.core.acceptance_utils import create_payment_reminder_for_acceptance, append_notes
from app.schemas.acceptance import (
    AcceptanceCreate,
    AcceptanceUpdate,
    AcceptanceResponse,
    AppendNotesRequest,
)

logger = logging.getLogger("app.acceptances")
router = APIRouter()


@router.get("", response_model=list[AcceptanceResponse])
async def list_acceptances(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """返回该项目所有验收记录，按 acceptance_date 倒序"""
    project = await db.get(Project, project_id)
    if not project or project.is_deleted:
        raise HTTPException(status_code=404, detail="项目不存在")

    result = await db.execute(
        select(Acceptance)
        .where(Acceptance.project_id == project_id)
        .order_by(Acceptance.acceptance_date.desc())
    )
    return list(result.scalars().all())


@router.get("/{acceptance_id}", response_model=AcceptanceResponse)
async def get_acceptance(
    project_id: int,
    acceptance_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """返回验收记录详情"""
    acc = await db.get(Acceptance, acceptance_id)
    if not acc or acc.project_id != project_id:
        raise HTTPException(status_code=404, detail="验收记录不存在")
    return acc


@router.post("", response_model=AcceptanceResponse, status_code=201)
async def create_acceptance(
    project_id: int,
    acc_in: AcceptanceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建验收记录。result=passed/conditional + trigger_payment_reminder=True 时事务内创建提醒"""
    project = await db.get(Project, project_id)
    if not project or project.is_deleted:
        raise HTTPException(status_code=404, detail="项目不存在")

    acc = Acceptance(
        project_id=project_id,
        acceptance_name=acc_in.acceptance_name,
        acceptance_date=acc_in.acceptance_date,
        acceptor_name=acc_in.acceptor_name,
        acceptor_title=acc_in.acceptor_title,
        result=acc_in.result,
        notes=acc_in.notes,
        trigger_payment_reminder=acc_in.trigger_payment_reminder,
        confirm_method=acc_in.confirm_method,
        milestone_id=acc_in.milestone_id,
    )
    db.add(acc)
    await db.flush()

    # 验收通过联动收款提醒
    if acc_in.result in ("passed", "conditional") and acc_in.trigger_payment_reminder:
        try:
            reminder_id = await create_payment_reminder_for_acceptance(
                acc_in.acceptance_name, acc.id, db
            )
            acc.reminder_id = reminder_id
        except Exception as e:
            logger.error("验收记录创建事务失败 | table=acceptances | project_id=%s | acceptance_id=%s | error=%s", project_id, acc.id, str(e))
            raise

    await db.commit()
    await db.refresh(acc)
    return acc


@router.put("/{acceptance_id}", response_model=AcceptanceResponse)
async def update_acceptance(
    project_id: int,
    acceptance_id: int,
    acc_in: AcceptanceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """全量更新。result 字段不可修改"""
    acc = await db.get(Acceptance, acceptance_id)
    if not acc or acc.project_id != project_id:
        raise HTTPException(status_code=404, detail="验收记录不存在")

    update_data = acc_in.model_dump(exclude_unset=True)
    if "result" in update_data:
        raise HTTPException(status_code=422, detail="验收结果不可修改")

    for field, value in update_data.items():
        setattr(acc, field, value)

    await db.commit()
    await db.refresh(acc)
    return acc


@router.patch("/{acceptance_id}", response_model=AcceptanceResponse)
async def patch_acceptance(
    project_id: int,
    acceptance_id: int,
    acc_in: AcceptanceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """部分更新。result 字段不可修改（PATCH 同样约束）"""
    return await update_acceptance(project_id, acceptance_id, acc_in, db, current_user)


@router.delete("/{acceptance_id}")
async def delete_acceptance(
    project_id: int,
    acceptance_id: int,
):
    """DELETE 返回 HTTP 405，不执行任何操作"""
    raise HTTPException(status_code=405, detail="验收记录禁止删除")


@router.patch("/{acceptance_id}/append-notes", response_model=AcceptanceResponse)
async def append_acceptance_notes(
    project_id: int,
    acceptance_id: int,
    notes_in: AppendNotesRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """追加 notes。原内容 + \\n + 新备注。原内容为空时直接存入"""
    acc = await db.get(Acceptance, acceptance_id)
    if not acc or acc.project_id != project_id:
        raise HTTPException(status_code=404, detail="验收记录不存在")

    acc.notes = append_notes(acc.notes, notes_in.notes)
    await db.commit()
    await db.refresh(acc)
    return acc
