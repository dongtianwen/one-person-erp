"""v1.11 模型与实验工具——版本号校验、冻结规则、关联管理、追溯查询。"""

import re
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    MODEL_VERSION_NO_PATTERN,
    MODEL_VERSION_FROZEN_STATUSES,
    MODEL_VERSION_FROZEN_FIELDS,
    EXPERIMENT_FROZEN_FIELDS,
)
from app.core.dataset_utils import mark_version_in_use, unmark_version_in_use
from app.core.logging import get_logger

logger = get_logger("model_utils")


def validate_model_version_no(version_no: str) -> bool:
    """校验模型版本号格式 ^v\\d+\\.\\d+\\.\\d+$。"""
    return bool(re.match(MODEL_VERSION_NO_PATTERN, version_no))


async def check_experiment_field_frozen(
    db: AsyncSession, experiment_id: int, updated_fields: set,
) -> list:
    """检查实验冻结字段——关联数据集版本后 EXPERIMENT_FROZEN_FIELDS 不可改。"""
    from app.models.training_experiment import ExperimentDatasetVersion

    stmt = select(func.count()).select_from(ExperimentDatasetVersion).where(
        ExperimentDatasetVersion.experiment_id == experiment_id,
    )
    result = await db.execute(stmt)
    has_links = result.scalar() > 0

    if not has_links:
        return []

    frozen = updated_fields & set(EXPERIMENT_FROZEN_FIELDS)
    if frozen:
        logger.warning("实验冻结拦截: experiment_id=%d, 被拒字段=%s", experiment_id, sorted(frozen))
    return sorted(frozen)


def check_model_version_field_frozen(
    version_status: str, updated_fields: set,
) -> list:
    """检查模型版本冻结字段——ready/delivered/deprecated 状态下冻结。"""
    if version_status not in MODEL_VERSION_FROZEN_STATUSES:
        return []
    frozen = updated_fields & set(MODEL_VERSION_FROZEN_FIELDS)
    if frozen:
        logger.warning("模型版本冻结拦截: status=%s, 被拒字段=%s", version_status, sorted(frozen))
    return sorted(frozen)


async def link_dataset_version_to_experiment(
    db: AsyncSession, experiment_id: int, version_id: int,
) -> None:
    """关联数据集版本到实验（原子事务）——自动设置 in_use。"""
    from app.models.training_experiment import ExperimentDatasetVersion

    link = ExperimentDatasetVersion(
        experiment_id=experiment_id,
        dataset_version_id=version_id,
    )
    db.add(link)
    await db.flush()
    await mark_version_in_use(db, version_id)
    logger.info("数据集版本 %d 已关联实验 %d，状态更新为 in_use", version_id, experiment_id)


async def unlink_dataset_version_from_experiment(
    db: AsyncSession, experiment_id: int, version_id: int,
) -> None:
    """解除关联（原子事务）——无其他引用时恢复 ready。"""
    from app.models.training_experiment import ExperimentDatasetVersion

    stmt = select(ExperimentDatasetVersion).where(
        ExperimentDatasetVersion.experiment_id == experiment_id,
        ExperimentDatasetVersion.dataset_version_id == version_id,
    )
    result = await db.execute(stmt)
    link = result.scalar_one_or_none()
    if link:
        await db.delete(link)
        await db.flush()
    await unmark_version_in_use(db, version_id)
    logger.info("数据集版本 %d 已解除与实验 %d 的关联", version_id, experiment_id)


async def get_experiment_traceability(
    db: AsyncSession, experiment_id: int,
) -> dict[str, Any]:
    """实验可追溯性——实验 + 关联的数据集版本 + 模型版本。"""
    from app.models.training_experiment import TrainingExperiment, ExperimentDatasetVersion
    from app.models.model_version import ModelVersion
    from app.models.dataset import DatasetVersion

    exp = await db.get(TrainingExperiment, experiment_id)
    if not exp:
        return {}

    # 关联的数据集版本
    dv_stmt = (
        select(DatasetVersion)
        .join(ExperimentDatasetVersion, ExperimentDatasetVersion.dataset_version_id == DatasetVersion.id)
        .where(ExperimentDatasetVersion.experiment_id == experiment_id)
    )
    dv_result = await db.execute(dv_stmt)
    dataset_versions = dv_result.scalars().all()

    # 产出的模型版本
    mv_stmt = select(ModelVersion).where(ModelVersion.experiment_id == experiment_id)
    mv_result = await db.execute(mv_stmt)
    model_versions = mv_result.scalars().all()

    return {
        "experiment": {
            "id": exp.id,
            "name": exp.name,
            "framework": exp.framework,
            "hyperparameters": exp.hyperparameters,
            "metrics": exp.metrics,
        },
        "dataset_versions": [
            {"id": v.id, "version_no": v.version_no, "status": v.status}
            for v in dataset_versions
        ],
        "model_versions": [
            {"id": m.id, "name": m.name, "version_no": m.version_no, "status": m.status}
            for m in model_versions
        ],
    }


async def get_model_version_traceability(
    db: AsyncSession, version_id: int,
) -> dict[str, Any]:
    """模型版本可追溯性——模型 + 实验 + 实验的数据集版本。"""
    from app.models.model_version import ModelVersion
    from app.models.training_experiment import ExperimentDatasetVersion
    from app.models.dataset import DatasetVersion

    mv = await db.get(ModelVersion, version_id)
    if not mv:
        return {}

    # 实验关联的数据集版本
    dv_stmt = (
        select(DatasetVersion)
        .join(ExperimentDatasetVersion, ExperimentDatasetVersion.dataset_version_id == DatasetVersion.id)
        .where(ExperimentDatasetVersion.experiment_id == mv.experiment_id)
    )
    dv_result = await db.execute(dv_stmt)
    dataset_versions = dv_result.scalars().all()

    return {
        "model_version": {
            "id": mv.id,
            "name": mv.name,
            "version_no": mv.version_no,
            "status": mv.status,
            "metrics": mv.metrics,
        },
        "experiment_id": mv.experiment_id,
        "dataset_versions": [
            {"id": v.id, "version_no": v.version_no, "status": v.status}
            for v in dataset_versions
        ],
    }


def get_experiment_metrics_summary(metrics: str | None) -> str:
    """提取训练实验的指标摘要用于前端显示。"""
    if not metrics:
        return "-"

    try:
        # 尝试解析JSON
        import json
        if isinstance(metrics, str):
            data = json.loads(metrics)
        else:
            data = metrics

        # 提取主要指标
        summary_parts = []
        if isinstance(data, dict):
            # 常见指标字段
            priority_fields = ['accuracy', 'loss', 'f1', 'precision', 'recall', 'iou']
            for field in priority_fields:
                if field in data:
                    summary_parts.append(f"{field}: {data[field]}")

            # 如果没有找到优先字段，显示前几个值
            if not summary_parts:
                for key, value in list(data.items())[:3]:
                    summary_parts.append(f"{key}: {value}")
        elif isinstance(data, list):
            summary_parts = [str(item) for item in data[:3]]

        return summary_parts[0] if summary_parts else str(data)
    except (json.JSONDecodeError, TypeError):
        return metrics[:100] if metrics else "-"
