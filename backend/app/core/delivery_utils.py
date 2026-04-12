"""v1.11 交付包工具——ready 前置检查、deliver 原子事务、验收、追溯查询。"""

from datetime import datetime
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    ACCEPTANCE_TYPE_MODEL,
    ACCEPTANCE_TYPE_DATASET,
)
from app.core.logging import get_logger

logger = get_logger("delivery_utils")


async def can_mark_ready(db: AsyncSession, package_id: int) -> bool:
    """检查交付包是否可以标记为 ready（至少关联一个模型版本或数据集版本）。"""
    from app.models.delivery_package import PackageModelVersion, PackageDatasetVersion

    mv_count = await db.execute(
        select(func.count()).select_from(PackageModelVersion).where(
            PackageModelVersion.package_id == package_id,
        )
    )
    dv_count = await db.execute(
        select(func.count()).select_from(PackageDatasetVersion).where(
            PackageDatasetVersion.package_id == package_id,
        )
    )
    total = mv_count.scalar() + dv_count.scalar()
    return total > 0


async def deliver_package(db: AsyncSession, package_id: int) -> dict[str, Any]:
    """原子交付——设置 delivered + delivered_at + 批量更新模型版本为 delivered。"""
    from app.models.delivery_package import DeliveryPackage, PackageModelVersion
    from app.models.model_version import ModelVersion

    pkg = await db.get(DeliveryPackage, package_id)
    if not pkg:
        raise ValueError("交付包不存在")
    if pkg.status != "ready":
        logger.warning("交付包 %d 交付失败: 当前状态=%s, 要求 ready", package_id, pkg.status)
        raise ValueError("仅 ready 状态可交付")

    # 更新包状态
    pkg.status = "delivered"
    pkg.delivered_at = datetime.utcnow()

    # 批量更新关联模型版本状态
    stmt = select(PackageModelVersion).where(
        PackageModelVersion.package_id == package_id,
    )
    result = await db.execute(stmt)
    links = result.scalars().all()
    for link in links:
        mv = await db.get(ModelVersion, link.model_version_id)
        if mv:
            mv.status = "delivered"

    await db.flush()
    logger.info("交付包 %d 已交付，%d 个模型版本状态更新", package_id, len(links))
    return {"package_id": package_id, "delivered_model_count": len(links)}


async def create_package_acceptance(
    db: AsyncSession,
    package_id: int,
    result: str,
    notes: str | None = None,
) -> dict[str, Any]:
    """创建交付包验收——自动判断类型、result=passed 时更新包状态。"""
    from app.models.delivery_package import DeliveryPackage, PackageModelVersion
    from app.models.acceptance import Acceptance

    pkg = await db.get(DeliveryPackage, package_id)
    if not pkg:
        raise ValueError("交付包不存在")

    # 检查是否已有验收记录
    stmt = select(func.count()).select_from(Acceptance).where(
        Acceptance.delivery_package_id == package_id,
    )
    count_result = await db.execute(stmt)
    if count_result.scalar() > 0:
        logger.warning("交付包 %d 验收失败: 已存在验收记录", package_id)
        raise ValueError("交付包已有验收记录")

    # 自动判断验收类型
    mv_count = await db.execute(
        select(func.count()).select_from(PackageModelVersion).where(
            PackageModelVersion.package_id == package_id,
        )
    )
    acceptance_type = ACCEPTANCE_TYPE_MODEL if mv_count.scalar() > 0 else ACCEPTANCE_TYPE_DATASET

    # 创建验收记录
    acceptance = Acceptance(
        project_id=pkg.project_id,
        acceptance_name=f"{pkg.name} 验收",
        acceptance_date=datetime.utcnow().date(),
        acceptor_name="系统",
        result=result,
        notes=notes,
        confirm_method="delivery_package",
        delivery_package_id=package_id,
        acceptance_type=acceptance_type,
    )
    db.add(acceptance)

    # result=passed 时更新包状态为 accepted
    if result == "passed":
        pkg.status = "accepted"

    await db.flush()
    logger.info("交付包 %d 验收完成: result=%s, type=%s", package_id, result, acceptance_type)
    return {
        "acceptance_id": acceptance.id,
        "acceptance_type": acceptance_type,
        "package_status": pkg.status,
    }


async def get_package_traceability(
    db: AsyncSession, package_id: int,
) -> dict[str, Any]:
    """交付包可追溯性——包 + 模型版本(含实验和数据集) + 数据集版本 + 验收。"""
    from app.models.delivery_package import (
        DeliveryPackage, PackageModelVersion, PackageDatasetVersion,
    )
    from app.models.model_version import ModelVersion
    from app.models.dataset import DatasetVersion
    from app.models.training_experiment import ExperimentDatasetVersion
    from app.models.acceptance import Acceptance

    pkg = await db.get(DeliveryPackage, package_id)
    if not pkg:
        return {}

    # 模型版本 + 实验 + 数据集版本
    mv_links = (await db.execute(
        select(PackageModelVersion).where(PackageModelVersion.package_id == package_id)
    )).scalars().all()

    model_versions_detail = []
    for link in mv_links:
        mv = await db.get(ModelVersion, link.model_version_id)
        if not mv:
            continue
        # 实验关联的数据集版本
        exp_dvs = (await db.execute(
            select(DatasetVersion)
            .join(ExperimentDatasetVersion, ExperimentDatasetVersion.dataset_version_id == DatasetVersion.id)
            .where(ExperimentDatasetVersion.experiment_id == mv.experiment_id)
        )).scalars().all()
        model_versions_detail.append({
            "model_version": {"id": mv.id, "name": mv.name, "version_no": mv.version_no, "status": mv.status},
            "experiment_id": mv.experiment_id,
            "dataset_versions": [{"id": v.id, "version_no": v.version_no} for v in exp_dvs],
        })

    # 数据集版本
    dv_links = (await db.execute(
        select(PackageDatasetVersion).where(PackageDatasetVersion.package_id == package_id)
    )).scalars().all()
    dataset_versions_detail = []
    for link in dv_links:
        dv = await db.get(DatasetVersion, link.dataset_version_id)
        if dv:
            dataset_versions_detail.append({"id": dv.id, "version_no": dv.version_no, "status": dv.status})

    # 验收记录
    acc_stmt = select(Acceptance).where(Acceptance.delivery_package_id == package_id)
    acc_result = await db.execute(acc_stmt)
    acceptance = acc_result.scalar_one_or_none()

    return {
        "package": {"id": pkg.id, "name": pkg.name, "status": pkg.status, "delivered_at": pkg.delivered_at.isoformat() if pkg.delivered_at else None},
        "model_versions": model_versions_detail,
        "dataset_versions": dataset_versions_detail,
        "acceptance": {
            "id": acceptance.id,
            "result": acceptance.result,
            "acceptance_type": acceptance.acceptance_type,
            "notes": acceptance.notes,
        } if acceptance else None,
    }
