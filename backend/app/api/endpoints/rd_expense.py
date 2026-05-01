"""v2.3 研发费用台账 API 端点。"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.rd_expense import RdExpense
from app.schemas.rd_expense import (
    RdExpenseCreate,
    RdExpenseUpdate,
    RdExpenseResponse,
    RdExpenseListResponse,
    RdSummaryResponse,
    RdStatusUpdateRequest,
)
from app.crud.rd_expense import rd_expense
from app.core.rd_expense_utils import write_rd_expense_excel
from app.core.constants import RD_CATEGORY_WHITELIST, RD_STATUS_LABELS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/rd-expenses", tags=["研发费用台账"])


@router.post("", response_model=RdExpenseResponse)
async def create_rd_expense(
    req: RdExpenseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if req.rd_sub_category:
        from app.core.constants import RD_SUB_TO_CATEGORY_MAP
        expected_cat = RD_SUB_TO_CATEGORY_MAP.get(req.rd_sub_category)
        if expected_cat and expected_cat != req.rd_category:
            raise HTTPException(
                status_code=400,
                detail=f"rd_sub_category '{req.rd_sub_category}' belongs to category '{expected_cat}', not '{req.rd_category}'"
            )
    rd_no = await rd_expense.generate_rd_no(db)
    record = await rd_expense.create(db, req, rd_no)
    return record


@router.get("", response_model=RdExpenseListResponse)
async def list_rd_expenses(
    project_id: int | None = Query(None),
    rd_category: str | None = Query(None, description="按大类过滤"),
    status: str | None = Query(None),
    year: int | None = Query(None, description="按年份过滤"),
    quarter: int | None = Query(None, ge=1, le=4, description="按季度过滤"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if rd_category and rd_category not in RD_CATEGORY_WHITELIST:
        raise HTTPException(status_code=400, detail=f"Invalid rd_category: {rd_category}")
    items, total = await rd_expense.get_multi(
        db,
        project_id=project_id,
        rd_category=rd_category,
        status=status,
        year=year,
        quarter=quarter,
        skip=skip,
        limit=limit,
    )
    return {"items": items, "total": total}


@router.get("/summary", response_model=RdSummaryResponse)
async def get_rd_summary(
    year: int | None = Query(None),
    quarter: int | None = Query(None, ge=1, le=4),
    accounting_period: str | None = Query(None, pattern=r"^\d{4}-\d{2}$"),
    project_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    summary = await rd_expense.get_summary(
        db,
        year=year,
        quarter=quarter,
        accounting_period=accounting_period,
        project_id=project_id,
    )
    return summary


@router.get("/{record_id}", response_model=RdExpenseResponse)
async def get_rd_expense(
    record_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = await rd_expense.get(db, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="研发费用记录不存在")
    return record


@router.put("/{record_id}", response_model=RdExpenseResponse)
async def update_rd_expense(
    record_id: int,
    req: RdExpenseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = await rd_expense.get(db, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="研发费用记录不存在")
    if req.rd_sub_category and req.rd_category is None:
        from app.core.constants import RD_SUB_TO_CATEGORY_MAP
        expected_cat = RD_SUB_TO_CATEGORY_MAP.get(req.rd_sub_category)
        if expected_cat and expected_cat != record.rd_category:
            raise HTTPException(
                status_code=400,
                detail=f"rd_sub_category belongs to category '{expected_cat}', current is '{record.rd_category}'"
            )
    updated = await rd_expense.update(db, record, req)
    return updated


@router.delete("/{record_id}")
async def delete_rd_expense(
    record_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    success = await rd_expense.delete(db, record_id)
    if not success:
        record = await rd_expense.get(db, record_id)
        if record is None:
            raise HTTPException(status_code=404, detail="研发费用记录不存在")
        raise HTTPException(status_code=400, detail="仅草稿状态的记录可删除")
    return {"deleted": True}


@router.patch("/{record_id}/status", response_model=RdExpenseResponse)
async def update_rd_status(
    record_id: int,
    req: RdStatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = await rd_expense.get(db, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="研发费用记录不存在")
    try:
        updated = await rd_expense.update_status(db, record, req.status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return updated


@router.get("/export/file")
async def export_rd_expenses(
    year: int | None = Query(None),
    quarter: int | None = Query(None, ge=1, le=4),
    accounting_period: str | None = Query(None),
    project_id: int | None = Query(None),
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from fastapi.responses import Response
    import traceback

    try:
        items, _ = await rd_expense.get_multi(
            db,
            project_id=project_id,
            status=status,
            year=year,
            quarter=quarter,
            skip=0,
            limit=10000,
        )
        if not items:
            raise HTTPException(status_code=404, detail="无符合条件的记录可导出")

        summary = await rd_expense.get_summary(
            db, year=year, quarter=quarter, accounting_period=accounting_period, project_id=project_id
        )
        buf = await write_rd_expense_excel(db, items, summary)

        period_label = accounting_period or (f"{year}Q{quarter}" if quarter else str(year or "全部"))
        filename = f"研发费用台账_{period_label}.xlsx"

        from urllib.parse import quote
        encoded_filename = quote(filename)
        ascii_period = accounting_period or (f"{year}Q{quarter}" if quarter else str(year or "all"))
        ascii_fallback = f"rd_expense_{ascii_period}.xlsx"

        return Response(
            content=buf.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=\"{ascii_fallback}\"; filename*=UTF-8''{encoded_filename}"},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"RD export error: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")


@router.post("/import-from-finance/{finance_record_id}", response_model=RdExpenseResponse)
async def import_from_finance(
    finance_record_id: int,
    req: RdExpenseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """从财务支出记录导入到研发费用台账。"""
    from sqlalchemy import select
    from app.models.finance import FinanceRecord

    # 1. 验证财务记录存在且为支出类型
    result = await db.execute(
        select(FinanceRecord).where(FinanceRecord.id == finance_record_id)
    )
    fin = result.scalar_one_or_none()
    if fin is None:
        raise HTTPException(status_code=404, detail="财务记录不存在")
    if fin.type != "expense":
        raise HTTPException(status_code=400, detail="仅支出类型记录可导入研发费用台账")

    # 2. 检查是否已关联（防重复导入）
    dup_result = await db.execute(
        select(RdExpense).where(
            RdExpense.finance_record_id == finance_record_id,
            RdExpense.is_deleted == False,
        )
    )
    if dup_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="该财务记录已归入研发费用台账，不可重复导入")

    # 3. 校验子分类与费用大类匹配
    if req.rd_sub_category:
        from app.core.constants import RD_SUB_TO_CATEGORY_MAP
        expected_cat = RD_SUB_TO_CATEGORY_MAP.get(req.rd_sub_category)
        if expected_cat and expected_cat != req.rd_category:
            raise HTTPException(
                status_code=400,
                detail=f"子分类 '{req.rd_sub_category}' 属于 '{expected_cat}' 大类，不是 '{req.rd_category}'"
            )

    # 4. 创建 RdExpense
    rd_no = await rd_expense.generate_rd_no(db)
    record = await rd_expense.create(db, req, rd_no)

    # 5. 回写 finance_record_id（create 时未设置，因为 schema 中 finance_record_id 可选）
    record.finance_record_id = finance_record_id
    await db.commit()
    await db.refresh(record)
    return record


@router.patch("/{record_id}/unlink-finance", response_model=RdExpenseResponse)
async def unlink_finance_record(
    record_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """解除研发费用与财务支出记录的关联。"""
    record = await rd_expense.get(db, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="研发费用记录不存在")
    if record.finance_record_id is None:
        raise HTTPException(status_code=400, detail="该记录未关联财务支出记录")

    record.finance_record_id = None
    await db.commit()
    await db.refresh(record)
    return record


@router.get("/meta/categories")
async def get_rd_categories(
    current_user: User = Depends(get_current_user),
):
    from app.core.constants import (
        RD_CATEGORY_LABELS,
        RD_SUB_CATEGORY_LABELS,
        RD_SUB_TO_CATEGORY_MAP,
    )
    categories = []
    for key, label in RD_CATEGORY_LABELS.items():
        subs = {
            sk: RD_SUB_CATEGORY_LABELS[sk]
            for sk, sc in RD_SUB_TO_CATEGORY_MAP.items()
            if sc == key
        }
        categories.append({
            "value": key,
            "label": label,
            "sub_categories": subs,
        })
    return {
        "categories": categories,
        "statuses": RD_STATUS_LABELS,
    }
