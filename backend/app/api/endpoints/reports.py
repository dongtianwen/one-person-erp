"""v2.1 深度报告 API。"""
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.report import Report

router = APIRouter()


class ReportGenerateRequest(BaseModel):
    report_type: str
    entity_id: int
    template_id: Optional[int] = None


@router.post("/generate")
async def generate_report(
    req: ReportGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """生成报告。"""
    from app.core.report_service import generate_report
    result = await generate_report(db, req.report_type, req.entity_id, req.template_id)
    return {"code": 0, "data": result}


@router.get("")
async def list_reports(
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[int] = Query(None),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查询报告列表。"""
    query = select(Report).where(Report.is_latest == 1)
    if entity_type:
        query = query.where(Report.entity_type == entity_type)
    if entity_id:
        query = query.where(Report.entity_id == entity_id)
    query = query.order_by(Report.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()

    count_query = select(func.count(Report.id)).where(Report.is_latest == 1)
    if entity_type:
        count_query = count_query.where(Report.entity_type == entity_type)
    if entity_id:
        count_query = count_query.where(Report.entity_id == entity_id)
    total = (await db.execute(count_query)).scalar() or 0

    return {"code": 0, "data": {
        "items": [
            {
                "id": r.id,
                "report_type": r.report_type,
                "entity_id": r.entity_id,
                "entity_type": r.entity_type,
                "version_no": r.version_no,
                "status": r.status,
                "llm_provider": r.llm_provider,
                "llm_model": r.llm_model,
                "generated_at": r.generated_at.isoformat() if r.generated_at else None,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in items
        ],
        "total": total,
    }}


@router.get("/{report_id}")
async def get_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查询报告详情。"""
    result = await db.execute(select(Report).where(Report.id == report_id))
    r = result.scalar_one_or_none()
    if not r:
        from app.core.exception_handlers import BusinessException
        from app.core.error_codes import ERROR_CODES
        raise BusinessException(
            status_code=404, detail=ERROR_CODES.get("NOT_FOUND", "报告不存在"), code="NOT_FOUND",
        )
    return {"code": 0, "data": {
        "id": r.id,
        "report_type": r.report_type,
        "entity_id": r.entity_id,
        "entity_type": r.entity_type,
        "template_id": r.template_id,
        "parent_report_id": r.parent_report_id,
        "version_no": r.version_no,
        "is_latest": r.is_latest,
        "content": r.content,
        "llm_filled_vars": r.llm_filled_vars,
        "llm_provider": r.llm_provider,
        "llm_model": r.llm_model,
        "status": r.status,
        "error_message": r.error_message,
        "generated_at": r.generated_at.isoformat() if r.generated_at else None,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }}


@router.delete("/{report_id}")
async def delete_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除报告。"""
    result = await db.execute(select(Report).where(Report.id == report_id))
    r = result.scalar_one_or_none()
    if not r:
        from app.core.exception_handlers import BusinessException
        from app.core.error_codes import ERROR_CODES
        raise BusinessException(
            status_code=404, detail=ERROR_CODES.get("NOT_FOUND", "报告不存在"), code="NOT_FOUND",
        )
    await db.delete(r)
    await db.commit()
    return {"code": 0, "data": {"deleted": True}}
