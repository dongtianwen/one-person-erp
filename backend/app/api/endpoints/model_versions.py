"""v1.11 模型版本 CRUD API 路由。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.model_version import ModelVersion
from app.models.training_experiment import TrainingExperiment
from app.core.constants import MODEL_VERSION_STATUS_WHITELIST
from app.core.model_utils import (
    validate_model_version_no,
    check_model_version_field_frozen,
    get_model_version_traceability,
)
from app.core.error_codes import ERROR_CODES

router = APIRouter()


@router.post("")
async def create_model_version(
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建模型版本（experiment_id 必填，版本号格式 ^v\\d+\\.\\d+\\.\\d+$）。"""
    experiment_id = data.get("experiment_id")
    if not experiment_id:
        raise HTTPException(status_code=422, detail="experiment_id 必填")

    exp = await db.get(TrainingExperiment, experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="训练实验不存在")

    version_no = data.get("version_no", "")
    if not validate_model_version_no(version_no):
        raise HTTPException(status_code=422, detail="版本号格式错误，要求 ^v\\d+\\.\\d+\\.\\d+$")

    mv = ModelVersion(
        project_id=exp.project_id,
        experiment_id=experiment_id,
        name=data["name"],
        version_no=version_no,
        status=data.get("status", "training"),
        metrics=data.get("metrics"),
        file_path=data.get("file_path"),
        notes=data.get("notes"),
    )
    db.add(mv)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="模型版本重复")
    await db.refresh(mv)
    return {"id": mv.id, "message": "创建成功"}


@router.get("")
async def list_model_versions(
    project_id: int | None = None,
    experiment_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取模型版本列表。"""
    stmt = select(ModelVersion)
    if project_id:
        stmt = stmt.where(ModelVersion.project_id == project_id)
    if experiment_id:
        stmt = stmt.where(ModelVersion.experiment_id == experiment_id)
    stmt = stmt.order_by(ModelVersion.created_at.desc())
    result = await db.execute(stmt)
    versions = result.scalars().all()

    # 获取所有相关实验的名称，避免 N+1 查询
    experiment_ids = set()
    for v in versions:
        if hasattr(v, 'experiment_id') and v.experiment_id:
            experiment_ids.add(v.experiment_id)

    exp_name_map = {}
    if experiment_ids:
        from app.models.training_experiment import TrainingExperiment
        stmt = select(TrainingExperiment).where(TrainingExperiment.id.in_(experiment_ids))
        result = await db.execute(stmt)
        experiments = result.scalars().all()
        exp_name_map = {e.id: e.name for e in experiments}

    result_list = [
        {
            "id": v.id,
            "project_id": v.project_id,
            "experiment_id": v.experiment_id,
            "experiment_name": exp_name_map.get(v.experiment_id, "-"),
            "name": v.name,
            "version_no": v.version_no,
            "status": v.status,
            "model_path": v.file_path,
            "metrics": v.metrics,
            "notes": v.notes,
        }
        for v in versions
    ]

    return {"data": result_list}


@router.get("/{version_id}")
async def get_model_version(
    version_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取模型版本详情。"""
    mv = await db.get(ModelVersion, version_id)
    if not mv:
        raise HTTPException(status_code=404, detail=ERROR_CODES["NOT_FOUND"])
    return {
        "id": mv.id,
        "project_id": mv.project_id,
        "experiment_id": mv.experiment_id,
        "name": mv.name,
        "version_no": mv.version_no,
        "status": mv.status,
        "model_path": mv.file_path,
        "metrics": mv.metrics,
        "file_path": mv.file_path,
        "notes": mv.notes,
    }


@router.put("/{version_id}")
async def update_model_version(
    version_id: int,
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新模型版本（冻结校验）。"""
    mv = await db.get(ModelVersion, version_id)
    if not mv:
        raise HTTPException(status_code=404, detail=ERROR_CODES["NOT_FOUND"])

    updated_fields = set(data.keys())
    frozen = check_model_version_field_frozen(mv.status, updated_fields)
    if frozen:
        raise HTTPException(
            status_code=409,
            detail=f"字段已冻结: {', '.join(frozen)}",
        )

    for field in ("metrics", "file_path", "notes"):
        if field in data:
            setattr(mv, field, data[field])

    await db.commit()
    return {"message": "更新成功"}


@router.delete("/{version_id}")
async def delete_model_version(
    version_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除模型版本（delivered 不可删除）。"""
    mv = await db.get(ModelVersion, version_id)
    if not mv:
        raise HTTPException(status_code=404, detail=ERROR_CODES["NOT_FOUND"])

    if mv.status == "delivered":
        raise HTTPException(
            status_code=409,
            detail=ERROR_CODES["DELIVERED_MODEL_CANNOT_DELETE"],
        )

    await db.delete(mv)
    await db.commit()
    return {"message": "删除成功"}


# ── 状态转换 ─────────────────────────────────────────────────────


@router.patch("/{version_id}/ready")
async def transition_ready(
    version_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """training → ready。"""
    mv = await db.get(ModelVersion, version_id)
    if not mv:
        raise HTTPException(status_code=404, detail=ERROR_CODES["NOT_FOUND"])

    if mv.status != "training":
        raise HTTPException(status_code=409, detail="仅 training 状态可转为 ready")

    mv.status = "ready"
    await db.commit()
    return {"message": "已标记为 ready"}


@router.patch("/{version_id}/deprecate")
async def transition_deprecate(
    version_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """ready → deprecated。"""
    mv = await db.get(ModelVersion, version_id)
    if not mv:
        raise HTTPException(status_code=404, detail=ERROR_CODES["NOT_FOUND"])

    if mv.status not in ("ready", "delivered"):
        raise HTTPException(status_code=409, detail="仅 ready/delivered 状态可转为 deprecated")

    mv.status = "deprecated"
    await db.commit()
    return {"message": "已标记为 deprecated"}


# ── 追溯查询 ─────────────────────────────────────────────────────


@router.get("/{version_id}/traceability")
async def model_version_traceability(
    version_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取模型版本可追溯性。"""
    result = await get_model_version_traceability(db, version_id)
    if not result:
        raise HTTPException(status_code=404, detail=ERROR_CODES["NOT_FOUND"])
    return result
