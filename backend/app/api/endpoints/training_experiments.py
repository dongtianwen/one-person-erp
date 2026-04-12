"""v1.11 训练实验 CRUD API 路由。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.training_experiment import TrainingExperiment, ExperimentDatasetVersion
from app.models.dataset import DatasetVersion
from app.core.model_utils import (
    check_experiment_field_frozen,
    link_dataset_version_to_experiment,
    unlink_dataset_version_from_experiment,
    get_experiment_traceability,
    get_experiment_metrics_summary,
)
from app.core.error_codes import ERROR_CODES

router = APIRouter()


@router.post("")
async def create_experiment(
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建训练实验。"""
    project_id = data.get("project_id")
    if not project_id:
        raise HTTPException(status_code=422, detail="project_id 必填")

    project = await db.get(Project, project_id)
    if not project or project.is_deleted:
        raise HTTPException(status_code=404, detail="项目不存在")

    exp = TrainingExperiment(
        project_id=project_id,
        name=data["name"],
        description=data.get("description"),
        framework=data.get("framework"),
        hyperparameters=data.get("hyperparameters"),
        metrics=data.get("metrics"),
        status=data.get("status", "draft"),
        notes=data.get("notes"),
    )
    db.add(exp)
    await db.commit()
    await db.refresh(exp)
    return {"id": exp.id, "message": "创建成功"}


@router.get("")
async def list_experiments(
    project_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取训练实验列表。"""
    stmt = select(TrainingExperiment)
    if project_id:
        stmt = stmt.where(TrainingExperiment.project_id == project_id)
    stmt = stmt.order_by(TrainingExperiment.created_at.desc())
    result = await db.execute(stmt)
    experiments = result.scalars().all()
    
    # 获取所有实验的关联数据集版本
    exp_ids = [e.id for e in experiments]
    if exp_ids:
        link_stmt = select(ExperimentDatasetVersion).where(
            ExperimentDatasetVersion.experiment_id.in_(exp_ids)
        )
        link_result = await db.execute(link_stmt)
        links = link_result.scalars().all()
        exp_version_map = {}
        for link in links:
            exp_id = link.experiment_id
            dv_id = link.dataset_version_id
            if exp_id not in exp_version_map:
                exp_version_map[exp_id] = []
            exp_version_map[exp_id].append(dv_id)
    
    result_list = []
    for e in experiments:
        item = {
            "id": e.id,
            "project_id": e.project_id,
            "name": e.name,
            "framework": e.framework,
            "metrics": e.metrics,
            "metrics_summary": get_experiment_metrics_summary(e.metrics) if e.metrics else "-",
            "status": e.status,
            "notes": e.notes,
            "dataset_version_ids": exp_version_map.get(e.id, []),
        }
        result_list.append(item)
    
    return {"data": result_list}


@router.get("/{experiment_id}")
async def get_experiment(
    experiment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取实验详情。"""
    exp = await db.get(TrainingExperiment, experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail=ERROR_CODES["NOT_FOUND"])
    return {
        "id": exp.id,
        "project_id": exp.project_id,
        "name": exp.name,
        "description": exp.description,
        "framework": exp.framework,
        "hyperparameters": exp.hyperparameters,
        "metrics": exp.metrics,
        "metrics_summary": get_experiment_metrics_summary(exp.metrics) if exp.metrics else "-",
        "status": exp.status,
        "started_at": exp.started_at.isoformat() if exp.started_at else None,
        "finished_at": exp.finished_at.isoformat() if exp.finished_at else None,
        "notes": exp.notes,
    }


@router.put("/{experiment_id}")
async def update_experiment(
    experiment_id: int,
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新训练实验（冻结校验）。"""
    exp = await db.get(TrainingExperiment, experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail=ERROR_CODES["NOT_FOUND"])

    updated_fields = set(data.keys())
    frozen = await check_experiment_field_frozen(db, experiment_id, updated_fields)
    if frozen:
        raise HTTPException(
            status_code=409,
            detail=f"字段已冻结: {', '.join(frozen)}",
        )

    for field in ("name", "description", "framework", "hyperparameters",
                   "metrics", "notes", "started_at", "finished_at"):
        if field in data:
            setattr(exp, field, data[field])

    await db.commit()
    return {"message": "更新成功"}


@router.delete("/{experiment_id}")
async def delete_experiment(
    experiment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除训练实验（有关联模型版本时拒绝）。"""
    from app.models.model_version import ModelVersion

    exp = await db.get(TrainingExperiment, experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail=ERROR_CODES["NOT_FOUND"])

    stmt = select(ModelVersion).where(ModelVersion.experiment_id == experiment_id)
    result = await db.execute(stmt)
    if result.scalars().first():
        raise HTTPException(status_code=409, detail="实验下存在模型版本，不可删除")

    await db.delete(exp)
    await db.commit()
    return {"message": "删除成功"}


# ── 数据集版本关联 ──────────────────────────────────────────────


@router.post("/{experiment_id}/dataset-versions")
async def link_dataset_version(
    experiment_id: int,
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """关联数据集版本到实验（自动设置 in_use）。"""
    version_id = data.get("dataset_version_id")
    if not version_id:
        raise HTTPException(status_code=422, detail="dataset_version_id 必填")

    dv = await db.get(DatasetVersion, version_id)
    if not dv:
        raise HTTPException(status_code=404, detail="数据集版本不存在")

    try:
        await link_dataset_version_to_experiment(db, experiment_id, version_id)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=409, detail=str(e))

    await db.commit()
    return {"message": "关联成功"}


@router.delete("/{experiment_id}/dataset-versions/{version_id}")
async def unlink_dataset_version(
    experiment_id: int,
    version_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """解除数据集版本关联（无其他引用时恢复 ready）。"""
    try:
        await unlink_dataset_version_from_experiment(db, experiment_id, version_id)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=409, detail=str(e))

    await db.commit()
    return {"message": "解除关联成功"}


@router.get("/{experiment_id}/dataset-versions")
async def list_linked_versions(
    experiment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取实验关联的数据集版本列表。"""
    stmt = (
        select(DatasetVersion)
        .join(ExperimentDatasetVersion, ExperimentDatasetVersion.dataset_version_id == DatasetVersion.id)
        .where(ExperimentDatasetVersion.experiment_id == experiment_id)
    )
    result = await db.execute(stmt)
    versions = result.scalars().all()
    return {
        "data": [
            {"id": v.id, "version_no": v.version_no, "status": v.status, "sample_count": v.sample_count}
            for v in versions
        ]
    }


# ── 追溯查询 ─────────────────────────────────────────────────────


@router.get("/{experiment_id}/traceability")
async def experiment_traceability(
    experiment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取实验可追溯性。"""
    result = await get_experiment_traceability(db, experiment_id)
    if not result:
        raise HTTPException(status_code=404, detail=ERROR_CODES["NOT_FOUND"])
    return result
