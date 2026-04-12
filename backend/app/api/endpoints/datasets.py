"""v1.11 数据集台账 CRUD API 路由。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.dataset import Dataset, DatasetVersion
from app.models.project import Project
from app.core.constants import (
    DATASET_TYPE_WHITELIST,
    DATASET_VERSION_STATUS_WHITELIST,
)
from app.core.dataset_utils import (
    validate_version_no,
    check_version_field_frozen,
    can_delete_dataset_version,
    get_project_dataset_summary,
)
from app.core.error_codes import ERROR_CODES

router = APIRouter()


# ── 数据集 CRUD ──────────────────────────────────────────────────


@router.post("")
async def create_dataset(
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建数据集（project_id 必填）。"""
    project_id = data.get("project_id")
    if not project_id:
        raise HTTPException(status_code=422, detail="project_id 必填")

    project = await db.get(Project, project_id)
    if not project or project.is_deleted:
        raise HTTPException(status_code=404, detail="项目不存在")

    dataset_type = data.get("dataset_type", "other")
    if dataset_type not in DATASET_TYPE_WHITELIST:
        raise HTTPException(status_code=422, detail=f"数据集类型必须在 {DATASET_TYPE_WHITELIST} 内")

    ds = Dataset(
        project_id=project_id,
        name=data["name"],
        dataset_type=dataset_type,
        description=data.get("description"),
    )
    db.add(ds)
    await db.commit()
    await db.refresh(ds)
    return {"id": ds.id, "message": "创建成功"}


@router.get("")
async def list_datasets(
    project_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取数据集列表，可按 project_id 过滤。"""
    stmt = select(Dataset)
    if project_id:
        stmt = stmt.where(Dataset.project_id == project_id)
    stmt = stmt.order_by(Dataset.created_at.desc())
    result = await db.execute(stmt)
    datasets = result.scalars().all()
    return {"data": [
        {
            "id": d.id,
            "project_id": d.project_id,
            "name": d.name,
            "dataset_type": d.dataset_type,
            "description": d.description,
        }
        for d in datasets
    ]}


@router.get("/{dataset_id}")
async def get_dataset(
    dataset_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取数据集详情（含版本列表）。"""
    ds = await db.get(Dataset, dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail=ERROR_CODES["NOT_FOUND"])

    stmt = select(DatasetVersion).where(
        DatasetVersion.dataset_id == dataset_id,
    ).order_by(DatasetVersion.created_at.desc())
    result = await db.execute(stmt)
    versions = result.scalars().all()

    return {
        "id": ds.id,
        "project_id": ds.project_id,
        "name": ds.name,
        "dataset_type": ds.dataset_type,
        "description": ds.description,
        "versions": [
            {
                "id": v.id,
                "version_no": v.version_no,
                "status": v.status,
                "sample_count": v.sample_count,
                "file_path": v.file_path,
                "data_source": v.data_source,
                "label_schema_version": v.label_schema_version,
                "change_summary": v.change_summary,
                "notes": v.notes,
            }
            for v in versions
        ],
    }


@router.put("/{dataset_id}")
async def update_dataset(
    dataset_id: int,
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新数据集基本信息。"""
    ds = await db.get(Dataset, dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail=ERROR_CODES["NOT_FOUND"])

    if "name" in data:
        ds.name = data["name"]
    if "dataset_type" in data:
        if data["dataset_type"] not in DATASET_TYPE_WHITELIST:
            raise HTTPException(status_code=422, detail="数据集类型不合法")
        ds.dataset_type = data["dataset_type"]
    if "description" in data:
        ds.description = data["description"]

    await db.commit()
    return {"message": "更新成功"}


@router.delete("/{dataset_id}")
async def delete_dataset(
    dataset_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除数据集（有关联版本时拒绝）。"""
    ds = await db.get(Dataset, dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail=ERROR_CODES["NOT_FOUND"])

    stmt = select(DatasetVersion).where(DatasetVersion.dataset_id == dataset_id)
    result = await db.execute(stmt)
    if result.first():
        raise HTTPException(status_code=409, detail="数据集下存在版本，不可删除")

    await db.delete(ds)
    await db.commit()
    return {"message": "删除成功"}


# ── 数据集版本 CRUD ──────────────────────────────────────────────


@router.post("/{dataset_id}/versions")
async def create_version(
    dataset_id: int,
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建数据集版本（version_no 格式 ^v\\d+\\.\\d+$）。"""
    ds = await db.get(Dataset, dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="数据集不存在")

    version_no = data.get("version_no", "")
    if not validate_version_no(version_no):
        raise HTTPException(status_code=422, detail="版本号格式错误，要求 ^v\\d+\\.\\d+$")

    # 禁止通过 API 直接设置 in_use
    if data.get("status") == "in_use":
        raise HTTPException(
            status_code=422,
            detail=ERROR_CODES["DATASET_VERSION_IN_USE"],
        )

    version = DatasetVersion(
        dataset_id=dataset_id,
        version_no=version_no,
        status=data.get("status", "draft"),
        sample_count=data.get("sample_count"),
        file_path=data.get("file_path"),
        data_source=data.get("data_source"),
        label_schema_version=data.get("label_schema_version"),
        change_summary=data.get("change_summary"),
        notes=data.get("notes"),
    )
    db.add(version)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="版本号重复")
    await db.refresh(version)
    return {"id": version.id, "message": "创建成功"}


@router.get("/{dataset_id}/versions")
async def list_versions(
    dataset_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取数据集版本列表。"""
    stmt = select(DatasetVersion).where(
        DatasetVersion.dataset_id == dataset_id,
    ).order_by(DatasetVersion.created_at.desc())
    result = await db.execute(stmt)
    versions = result.scalars().all()
    return {"data": [
        {
            "id": v.id,
            "version_no": v.version_no,
            "status": v.status,
            "sample_count": v.sample_count,
            "file_path": v.file_path,
            "data_source": v.data_source,
            "label_schema_version": v.label_schema_version,
            "change_summary": v.change_summary,
            "notes": v.notes,
        }
        for v in versions
    ]}


@router.get("/versions/{version_id}")
async def get_version(
    version_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取数据集版本详情。"""
    version = await db.get(DatasetVersion, version_id)
    if not version:
        raise HTTPException(status_code=404, detail=ERROR_CODES["NOT_FOUND"])
    return {
        "id": version.id,
        "dataset_id": version.dataset_id,
        "version_no": version.version_no,
        "status": version.status,
        "sample_count": version.sample_count,
        "file_path": version.file_path,
        "data_source": version.data_source,
        "label_schema_version": version.label_schema_version,
        "change_summary": version.change_summary,
        "notes": version.notes,
    }


@router.put("/versions/{version_id}")
async def update_version(
    version_id: int,
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新数据集版本（冻结字段校验）。"""
    version = await db.get(DatasetVersion, version_id)
    if not version:
        raise HTTPException(status_code=404, detail=ERROR_CODES["NOT_FOUND"])

    updated_fields = set(data.keys())
    frozen = check_version_field_frozen(version.status, updated_fields)
    if frozen:
        raise HTTPException(
            status_code=409,
            detail=f"字段已冻结: {', '.join(frozen)}",
        )

    for field in ("sample_count", "file_path", "data_source",
                   "label_schema_version", "change_summary", "notes"):
        if field in data:
            setattr(version, field, data[field])

    await db.commit()
    return {"message": "更新成功"}


@router.delete("/versions/{version_id}")
async def delete_version(
    version_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除数据集版本（in_use 不可删除）。"""
    version = await db.get(DatasetVersion, version_id)
    if not version:
        raise HTTPException(status_code=404, detail=ERROR_CODES["NOT_FOUND"])

    if not can_delete_dataset_version(version.status):
        raise HTTPException(
            status_code=409,
            detail=ERROR_CODES["VERSION_IN_USE_CANNOT_DELETE"],
        )

    await db.delete(version)
    await db.commit()
    return {"message": "删除成功"}


# ── 状态转换 ─────────────────────────────────────────────────────


@router.patch("/versions/{version_id}/ready")
async def transition_ready(
    version_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """将版本标记为 ready（核心字段冻结）。"""
    version = await db.get(DatasetVersion, version_id)
    if not version:
        raise HTTPException(status_code=404, detail=ERROR_CODES["NOT_FOUND"])

    if version.status != "draft":
        raise HTTPException(status_code=409, detail="仅 draft 状态可转为 ready")

    version.status = "ready"
    await db.commit()
    return {"message": "已标记为 ready"}


@router.patch("/versions/{version_id}/archive")
async def transition_archive(
    version_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """将版本标记为 archived。"""
    version = await db.get(DatasetVersion, version_id)
    if not version:
        raise HTTPException(status_code=404, detail=ERROR_CODES["NOT_FOUND"])

    if version.status not in ("ready", "in_use"):
        raise HTTPException(status_code=409, detail="仅 ready/in_use 状态可转为 archived")

    version.status = "archived"
    await db.commit()
    return {"message": "已标记为 archived"}


# ── 项目维度汇总 ─────────────────────────────────────────────────


@router.get("/projects/{project_id}/summary")
async def project_dataset_summary(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取项目下数据集汇总。"""
    return await get_project_dataset_summary(db, project_id)
