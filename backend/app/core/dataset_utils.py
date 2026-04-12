"""v1.11 数据集工具——版本号校验、冻结规则、in_use 管理。"""

import re
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    DATASET_VERSION_NO_PATTERN,
    DATASET_VERSION_STATUS_WHITELIST,
    DATASET_VERSION_FROZEN_STATUSES,
    DATASET_VERSION_FROZEN_FIELDS,
)
from app.core.logging import get_logger

logger = get_logger("dataset_utils")


def validate_version_no(version_no: str) -> bool:
    """校验数据集版本号格式 ^v\\d+\\.\\d+$。"""
    return bool(re.match(DATASET_VERSION_NO_PATTERN, version_no))


async def get_next_version_no(db: AsyncSession, dataset_id: int) -> str:
    """获取数据集下一个可用版本号（递增次版本号）。"""
    from app.models.dataset import DatasetVersion

    stmt = select(func.max(DatasetVersion.version_no)).where(
        DatasetVersion.dataset_id == dataset_id,
    )
    result = await db.execute(stmt)
    max_ver = result.scalar_one_or_none()
    if not max_ver:
        return "v1.0"
    match = re.match(r"^v(\d+)\.(\d+)$", max_ver)
    if not match:
        return "v1.0"
    major = int(match.group(1))
    minor = int(match.group(2)) + 1
    return f"v{major}.{minor}"


def check_version_field_frozen(version_status: str, updated_fields: set) -> list:
    """返回被冻结的字段列表，空列表表示无冻结字段。

    冻结条件：status in (ready, in_use, archived) 时，
    DATASET_VERSION_FROZEN_FIELDS 中的字段不可修改。
    notes 和 change_summary 任何状态均可修改。
    """
    if version_status not in DATASET_VERSION_FROZEN_STATUSES:
        return []
    frozen = updated_fields & set(DATASET_VERSION_FROZEN_FIELDS)
    if frozen:
        logger.warning("数据集版本冻结拦截: status=%s, 被拒字段=%s", version_status, sorted(frozen))
    return sorted(frozen)


async def mark_version_in_use(db: AsyncSession, version_id: int) -> None:
    """将数据集版本状态原子更新为 in_use（仅从 ready 转换）。"""
    from app.models.dataset import DatasetVersion

    stmt = select(DatasetVersion).where(DatasetVersion.id == version_id)
    result = await db.execute(stmt)
    version = result.scalar_one_or_none()
    if version and version.status == "ready":
        version.status = "in_use"
        await db.flush()
        logger.info("数据集版本 %d 状态更新为 in_use", version_id)


async def unmark_version_in_use(db: AsyncSession, version_id: int) -> None:
    """取消 in_use 状态——无其他实验引用时恢复为 ready（原子事务）。"""
    from app.models.dataset import DatasetVersion
    from app.models.training_experiment import ExperimentDatasetVersion

    # 检查是否还有其他实验引用
    stmt = select(func.count()).select_from(ExperimentDatasetVersion).where(
        ExperimentDatasetVersion.dataset_version_id == version_id,
    )
    result = await db.execute(stmt)
    ref_count = result.scalar()
    if ref_count == 0:
        ver_stmt = select(DatasetVersion).where(DatasetVersion.id == version_id)
        ver_result = await db.execute(ver_stmt)
        version = ver_result.scalar_one_or_none()
        if version and version.status == "in_use":
            version.status = "ready"
            await db.flush()
            logger.info("数据集版本 %d 无引用，状态恢复为 ready", version_id)


def can_delete_dataset_version(version_status: str) -> bool:
    """in_use 版本不可删除。"""
    return version_status != "in_use"


async def get_project_dataset_summary(db: AsyncSession, project_id: int) -> dict[str, Any]:
    """获取项目下数据集汇总信息。"""
    from app.models.dataset import Dataset, DatasetVersion

    ds_stmt = select(Dataset).where(Dataset.project_id == project_id)
    ds_result = await db.execute(ds_stmt)
    datasets = ds_result.scalars().all()

    items = []
    for ds in datasets:
        ver_stmt = select(DatasetVersion).where(
            DatasetVersion.dataset_id == ds.id,
        ).order_by(DatasetVersion.created_at.desc())
        ver_result = await db.execute(ver_stmt)
        versions = ver_result.scalars().all()
        items.append({
            "id": ds.id,
            "name": ds.name,
            "dataset_type": ds.dataset_type,
            "description": ds.description,
            "version_count": len(versions),
            "versions": [
                {
                    "id": v.id,
                    "version_no": v.version_no,
                    "status": v.status,
                    "sample_count": v.sample_count,
                    "data_source": v.data_source,
                    "label_schema_version": v.label_schema_version,
                    "change_summary": v.change_summary,
                    "notes": v.notes,
                }
                for v in versions
            ],
        })

    return {
        "project_id": project_id,
        "dataset_count": len(datasets),
        "datasets": items,
    }
