"""v1.11 交付包 CRUD API 路由。"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.delivery_package import (
    DeliveryPackage, PackageModelVersion, PackageDatasetVersion,
)
from app.models.model_version import ModelVersion
from app.models.dataset import DatasetVersion
from app.core.delivery_utils import (
    can_mark_ready,
    deliver_package,
    create_package_acceptance,
    get_package_traceability,
)
from app.core.error_codes import ERROR_CODES

router = APIRouter()


@router.post("")
async def create_package(
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建交付包（project_id 必填，默认 draft）。"""
    project_id = data.get("project_id")
    if not project_id:
        raise HTTPException(status_code=422, detail="project_id 必填")

    project = await db.get(Project, project_id)
    if not project or project.is_deleted:
        raise HTTPException(status_code=404, detail="项目不存在")

    pkg = DeliveryPackage(
        project_id=project_id,
        name=data["name"],
        description=data.get("description"),
        notes=data.get("notes"),
    )
    db.add(pkg)
    await db.commit()
    await db.refresh(pkg)
    return {"id": pkg.id, "message": "创建成功"}


@router.get("")
async def list_packages(
    project_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取交付包列表。"""
    stmt = select(DeliveryPackage)
    if project_id:
        stmt = stmt.where(DeliveryPackage.project_id == project_id)
    stmt = stmt.order_by(DeliveryPackage.created_at.desc())
    result = await db.execute(stmt)
    packages = result.scalars().all()
    return {
        "data": [
            {
                "id": p.id,
                "project_id": p.project_id,
                "name": p.name,
                "status": p.status,
                "description": p.description,
                "delivered_at": p.delivered_at.isoformat() if p.delivered_at else None,
                "notes": p.notes,
            }
            for p in packages
        ]
    }


@router.get("/{package_id}")
async def get_package(
    package_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取交付包详情。"""
    pkg = await db.get(DeliveryPackage, package_id)
    if not pkg:
        raise HTTPException(status_code=404, detail=ERROR_CODES["NOT_FOUND"])
    return {
        "id": pkg.id,
        "project_id": pkg.project_id,
        "name": pkg.name,
        "status": pkg.status,
        "description": pkg.description,
        "delivered_at": pkg.delivered_at.isoformat() if pkg.delivered_at else None,
        "notes": pkg.notes,
    }


@router.put("/{package_id}")
async def update_package(
    package_id: int,
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新交付包基本信息。"""
    pkg = await db.get(DeliveryPackage, package_id)
    if not pkg:
        raise HTTPException(status_code=404, detail=ERROR_CODES["NOT_FOUND"])

    for field in ("name", "description", "notes"):
        if field in data:
            setattr(pkg, field, data[field])

    await db.commit()
    return {"message": "更新成功"}


@router.delete("/{package_id}")
async def delete_package(
    package_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除交付包（accepted 不可删除）。"""
    pkg = await db.get(DeliveryPackage, package_id)
    if not pkg:
        raise HTTPException(status_code=404, detail=ERROR_CODES["NOT_FOUND"])

    if pkg.status == "accepted":
        raise HTTPException(
            status_code=409,
            detail=ERROR_CODES["ACCEPTED_PACKAGE_CANNOT_DELETE"],
        )

    await db.delete(pkg)
    await db.commit()
    return {"message": "删除成功"}


# ── 模型版本关联 ─────────────────────────────────────────────────


@router.post("/{package_id}/model-versions")
async def link_model_version(
    package_id: int,
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """关联模型版本到交付包。"""
    mv_id = data.get("model_version_id")
    if not mv_id:
        raise HTTPException(status_code=422, detail="model_version_id 必填")

    mv = await db.get(ModelVersion, mv_id)
    if not mv:
        raise HTTPException(status_code=404, detail="模型版本不存在")

    link = PackageModelVersion(package_id=package_id, model_version_id=mv_id)
    db.add(link)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="模型版本已在交付包中")

    return {"message": "关联成功"}


@router.delete("/{package_id}/model-versions/{model_version_id}")
async def unlink_model_version(
    package_id: int,
    model_version_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """解除模型版本关联。"""
    stmt = select(PackageModelVersion).where(
        PackageModelVersion.package_id == package_id,
        PackageModelVersion.model_version_id == model_version_id,
    )
    result = await db.execute(stmt)
    link = result.scalar_one_or_none()
    if link:
        await db.delete(link)
        await db.commit()
    return {"message": "解除关联成功"}


# ── 数据集版本关联 ──────────────────────────────────────────────


@router.post("/{package_id}/dataset-versions")
async def link_dataset_version(
    package_id: int,
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """关联数据集版本到交付包。"""
    dv_id = data.get("dataset_version_id")
    if not dv_id:
        raise HTTPException(status_code=422, detail="dataset_version_id 必填")

    dv = await db.get(DatasetVersion, dv_id)
    if not dv:
        raise HTTPException(status_code=404, detail="数据集版本不存在")

    link = PackageDatasetVersion(package_id=package_id, dataset_version_id=dv_id)
    db.add(link)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="数据集版本已在交付包中")

    return {"message": "关联成功"}


@router.delete("/{package_id}/dataset-versions/{dataset_version_id}")
async def unlink_dataset_version(
    package_id: int,
    dataset_version_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """解除数据集版本关联。"""
    stmt = select(PackageDatasetVersion).where(
        PackageDatasetVersion.package_id == package_id,
        PackageDatasetVersion.dataset_version_id == dataset_version_id,
    )
    result = await db.execute(stmt)
    link = result.scalar_one_or_none()
    if link:
        await db.delete(link)
        await db.commit()
    return {"message": "解除关联成功"}


# ── 交付与验收 ──────────────────────────────────────────────────


@router.patch("/{package_id}/ready")
async def transition_ready(
    package_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """标记为 ready（需要至少一个关联内容）。"""
    pkg = await db.get(DeliveryPackage, package_id)
    if not pkg:
        raise HTTPException(status_code=404, detail=ERROR_CODES["NOT_FOUND"])

    if not await can_mark_ready(db, package_id):
        raise HTTPException(
            status_code=422,
            detail=ERROR_CODES["PACKAGE_EMPTY_CANNOT_READY"],
        )

    pkg.status = "ready"
    await db.commit()
    return {"message": "已标记为 ready"}


@router.patch("/{package_id}/deliver")
async def deliver(
    package_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """交付（原子事务）。"""
    try:
        result = await deliver_package(db, package_id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    await db.commit()
    return {"message": "交付成功", **result}


@router.post("/{package_id}/acceptance")
async def create_acceptance(
    package_id: int,
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建验收记录（delivery_package_id 必须锁定到当前包）。"""
    dp_id = data.get("delivery_package_id")
    if not dp_id:
        raise HTTPException(status_code=422, detail="delivery_package_id 必填")
    if dp_id != package_id:
        raise HTTPException(status_code=422, detail=ERROR_CODES["PACKAGE_ID_MISMATCH"])

    result_val = data.get("result")
    if not result_val:
        raise HTTPException(status_code=422, detail="result 必填")

    try:
        result = await create_package_acceptance(
            db, package_id, result_val, data.get("notes"),
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    await db.commit()
    return {"message": "验收记录已创建", **result}


@router.get("/{package_id}/acceptance")
async def get_acceptance(
    package_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取交付包的验收记录。"""
    from app.models.acceptance import Acceptance

    stmt = select(Acceptance).where(Acceptance.delivery_package_id == package_id)
    result = await db.execute(stmt)
    acceptance = result.scalar_one_or_none()
    if not acceptance:
        return None
    return {
        "data": {
            "id": acceptance.id,
            "result": acceptance.result,
            "acceptance_type": acceptance.acceptance_type,
            "notes": acceptance.notes,
        }
    }


# ── 追溯查询 ─────────────────────────────────────────────────────


@router.get("/{package_id}/traceability")
async def package_traceability(
    package_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取交付包完整追溯链。"""
    result = await get_package_traceability(db, package_id)
    if not result:
        raise HTTPException(status_code=404, detail=ERROR_CODES["NOT_FOUND"])
    return {"data": result}
