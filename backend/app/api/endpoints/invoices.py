"""v1.8 发票台账 API 端点——完整 CRUD 和状态流转。"""

from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.logging import get_logger
from app.core.constants import INVOICE_STATUS_WHITELIST
from app.crud.invoice import invoice as invoice_crud
from app.database import get_db
from app.models.user import User
from app.schemas.invoice import (
    InvoiceCreate,
    InvoiceListResponse,
    InvoiceResponse,
    InvoiceStatusUpdate,
    InvoiceSummaryResponse,
    InvoiceSummary,
    InvoiceContractResponse,
    InvoiceUpdate,
)

logger = get_logger("invoices")
router = APIRouter()


@router.post("", response_model=InvoiceResponse, status_code=201)
async def create_invoice(
    invoice_in: InvoiceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    创建发票。

    - 自动生成发票编号（INV-YYYYMMDD-序号）
    - 自动计算税额和价税合计
    - 校验累计金额不超合同金额
    """
    try:
        db_obj = await invoice_crud.create(db, invoice_in)
        logger.info(f"发票创建成功: {db_obj.invoice_no}, 用户: {current_user.username}")
        return InvoiceResponse.model_validate(db_obj)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建发票失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=InvoiceListResponse)
async def list_invoices(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    contract_id: Optional[int] = None,
    status: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取发票列表。

    - 支持分页
    - 支持按合同、状态、日期范围筛选
    - 按发票日期倒序排列
    """
    if status and status not in INVOICE_STATUS_WHITELIST:
        raise HTTPException(status_code=422, detail=f"状态值无效，可选: {INVOICE_STATUS_WHITELIST}")

    items, total = await invoice_crud.list(
        db,
        skip=skip,
        limit=limit,
        contract_id=contract_id,
        invoice_status=status,
        start_date=start_date,
        end_date=end_date,
    )

    return InvoiceListResponse(
        items=[InvoiceResponse.model_validate(i) for i in items],
        total=total,
        page=(skip // limit) + 1,
        page_size=limit,
    )


@router.get("/summary", response_model=InvoiceSummaryResponse)
async def get_invoice_summary(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取发票汇总统计。

    - 按状态分组：count 和 total_amount
    - 支持日期范围筛选
    """
    summary = await invoice_crud.get_summary(db, start_date, end_date)

    return InvoiceSummaryResponse(
        draft=InvoiceSummary(**summary["draft"]),
        issued=InvoiceSummary(**summary["issued"]),
        received=InvoiceSummary(**summary["received"]),
        verified=InvoiceSummary(**summary["verified"]),
        cancelled=InvoiceSummary(**summary["cancelled"]),
    )


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取单个发票详情。"""
    db_obj = await invoice_crud.get(db, invoice_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="发票不存在")
    return InvoiceResponse.model_validate(db_obj)


@router.put("/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(
    invoice_id: int,
    invoice_in: InvoiceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    更新发票（全量更新）。

    - draft 状态：可更新所有字段
    - issued 状态：仅可更新 notes
    - verified/cancelled 状态：不可修改
    """
    db_obj = await invoice_crud.get(db, invoice_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="发票不存在")

    try:
        updated_obj = await invoice_crud.update(db, db_obj, invoice_in)
        logger.info(f"发票更新成功: {db_obj.invoice_no}, 用户: {current_user.username}")
        return InvoiceResponse.model_validate(updated_obj)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新发票失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{invoice_id}", response_model=InvoiceResponse)
async def partial_update_invoice(
    invoice_id: int,
    invoice_in: InvoiceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    部分更新发票。

    - draft 状态：可更新所有字段
    - issued 状态：仅可更新 notes
    - verified/cancelled 状态：不可修改
    """
    db_obj = await invoice_crud.get(db, invoice_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="发票不存在")

    try:
        updated_obj = await invoice_crud.update(db, db_obj, invoice_in)
        logger.info(f"发票部分更新成功: {db_obj.invoice_no}, 用户: {current_user.username}")
        return InvoiceResponse.model_validate(updated_obj)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"部分更新发票失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{invoice_id}", status_code=204)
async def delete_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    删除发票。

    - 仅允许删除 draft 状态的发票
    - verified/cancelled 状态不可删除
    """
    db_obj = await invoice_crud.get(db, invoice_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="发票不存在")

    try:
        await invoice_crud.delete(db, db_obj)
        logger.info(f"发票删除成功: {db_obj.invoice_no}, 用户: {current_user.username}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除发票失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{invoice_id}/issue", response_model=InvoiceResponse)
async def issue_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    开具发票。

    - 状态从 draft/received → issued
    - 设置 issued_at 时间戳
    """
    db_obj = await invoice_crud.get(db, invoice_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="发票不存在")

    try:
        updated_obj = await invoice_crud.issue(db, db_obj)
        logger.info(f"发票开具成功: {db_obj.invoice_no}, 用户: {current_user.username}")
        return InvoiceResponse.model_validate(updated_obj)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"开具发票失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{invoice_id}/receive", response_model=InvoiceResponse)
async def receive_invoice(
    invoice_id: int,
    status_update: InvoiceStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    确认收票。

    - 状态从 draft/issued → received
    - 设置 received_at 时间戳和 received_by
    """
    db_obj = await invoice_crud.get(db, invoice_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="发票不存在")

    try:
        updated_obj = await invoice_crud.receive(
            db, db_obj, received_by=status_update.received_by
        )
        logger.info(f"发票收票成功: {db_obj.invoice_no}, 用户: {current_user.username}")
        return InvoiceResponse.model_validate(updated_obj)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"收票失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{invoice_id}/verify", response_model=InvoiceResponse)
async def verify_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    核销发票。

    - 状态从 draft/issued/received → verified（终态）
    - 设置 verified_at 时间戳
    """
    db_obj = await invoice_crud.get(db, invoice_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="发票不存在")

    try:
        updated_obj = await invoice_crud.verify(db, db_obj)
        logger.info(f"发票核销成功: {db_obj.invoice_no}, 用户: {current_user.username}")
        return InvoiceResponse.model_validate(updated_obj)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"核销发票失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{invoice_id}/cancel", response_model=InvoiceResponse)
async def cancel_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    作废发票。

    - 从非终态状态 → cancelled（终态）
    - verified 状态不可作废
    """
    db_obj = await invoice_crud.get(db, invoice_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="发票不存在")

    try:
        updated_obj = await invoice_crud.cancel(db, db_obj)
        logger.info(f"发票作废成功: {db_obj.invoice_no}, 用户: {current_user.username}")
        return InvoiceResponse.model_validate(updated_obj)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"作废发票失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
