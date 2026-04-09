"""v1.8 财务导出 API 端点——数据导出与批次追溯。"""

from datetime import date
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.api.deps import get_current_user
from app.core.constants import EXPORT_FORMAT_SUPPORTED
from app.core.export_utils import export_to_excel, V18_EXPORT_DIR
from app.core.logging import get_logger
from app.database import get_db
from app.models.export_batch import ExportBatch
from app.models.user import User
from app.schemas.export import (
    ExportCreateResponse,
    ExportRequest,
    ExportBatchListResponse,
    ExportBatchResponse,
)

logger = get_logger("export")
router = APIRouter()


@router.post("", response_model=ExportCreateResponse, status_code=201)
async def create_export(
    export_in: ExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    创建导出批次。

    - 支持导出类型：contracts, payments, invoices
    - 支持格式：generic（本版本仅支持此格式）
    - 支持按会计期间或日期范围筛选
    - 返回批次 ID 和文件路径
    """
    try:
        result = await export_to_excel(
            db,
            export_type=export_in.export_type,
            filters={
                "start_date": export_in.start_date,
                "end_date": export_in.end_date,
                "accounting_period": export_in.accounting_period,
            },
            target_format=export_in.target_format,
        )
        logger.info(
            f"导出创建成功: {result['batch_id']}, 类型: {export_in.export_type}, "
            f"用户: {current_user.username}"
        )
        return ExportCreateResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NotImplementedError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建导出失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/batches", response_model=ExportBatchListResponse)
async def list_export_batches(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    export_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取导出批次列表。

    - 支持分页
    - 支持按导出类型筛选
    - 按创建时间倒序排列
    """
    stmt = select(ExportBatch)

    if export_type:
        stmt = stmt.where(ExportBatch.export_type == export_type)

    # 获取总数
    count_stmt = select(func.count()).select_from(ExportBatch)
    if export_type:
        count_stmt = count_stmt.where(ExportBatch.export_type == export_type)
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    # 分页查询
    stmt = stmt.order_by(ExportBatch.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    items = result.scalars().all()

    return ExportBatchListResponse(
        items=[ExportBatchResponse.model_validate(i) for i in items],
        total=total,
        page=(skip // limit) + 1,
        page_size=limit,
    )


@router.get("/batches/{batch_id}", response_model=ExportBatchResponse)
async def get_export_batch(
    batch_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取单个导出批次详情。"""
    stmt = select(ExportBatch).where(ExportBatch.batch_id == batch_id)
    result = await db.execute(stmt)
    batch = result.scalar_one_or_none()

    if not batch:
        raise HTTPException(status_code=404, detail="导出批次不存在")

    return ExportBatchResponse.model_validate(batch)


@router.get("/download/{batch_id}")
async def download_export_file(
    batch_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    下载导出文件。

    - 返回 Excel 文件
    - 如果文件不存在返回 404
    """
    stmt = select(ExportBatch).where(ExportBatch.batch_id == batch_id)
    result = await db.execute(stmt)
    batch = result.scalar_one_or_none()

    if not batch:
        raise HTTPException(status_code=404, detail="导出批次不存在")

    if not batch.file_path:
        raise HTTPException(status_code=404, detail="导出文件不存在")

    file_path = Path(batch.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="导出文件不存在")

    logger.info(f"文件下载: {batch_id}, 用户: {current_user.username}")

    return FileResponse(
        path=str(file_path),
        filename=file_path.name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
