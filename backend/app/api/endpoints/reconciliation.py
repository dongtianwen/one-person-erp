"""v1.8 会计期间对账 API 端点——期间汇总、客户分解、状态同步。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.logging import get_logger
from app.core.reconciliation_utils import (
    generate_reconciliation_report,
    get_available_periods,
    sync_reconciliation_status,
)
from app.database import get_db
from app.models.user import User
from app.schemas.reconciliation import (
    ReconciliationReport,
    SyncRequest,
    SyncResponse,
    PeriodListResponse,
)

logger = get_logger("reconciliation")
router = APIRouter()


@router.get("", response_model=PeriodListResponse)
async def list_periods(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取所有有数据的会计期间列表。"""
    periods = await get_available_periods(db)
    return PeriodListResponse(periods=periods)


@router.get("/{accounting_period}", response_model=ReconciliationReport)
async def get_report(
    accounting_period: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取指定会计期间的对账报表。"""
    try:
        report = await generate_reconciliation_report(db, accounting_period)
        logger.info(f"对账报表查询成功: {accounting_period}, 用户: {current_user.username}")
        return report
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"生成对账报表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync", response_model=SyncResponse)
async def sync_status(
    sync_in: SyncRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """同步对账状态。"""
    try:
        updated_count = await sync_reconciliation_status(db, sync_in.record_ids)
        logger.info(
            f"对账状态同步成功: 更新 {updated_count} 条记录, "
            f"用户: {current_user.username}"
        )
        return SyncResponse(updated_count=updated_count)
    except Exception as e:
        logger.error(f"同步对账状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
