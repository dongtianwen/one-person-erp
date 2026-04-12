"""v1.9 三表数据一致性校验 API 路由。"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.core.consistency_utils import (
    check_contract_consistency,
    check_all_contracts_consistency,
)

router = APIRouter()


@router.get("/consistency-check")
async def get_consistency_check(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取全量一致性校验报告（只读）。"""
    return await check_all_contracts_consistency(db)


@router.get("/consistency-check/{contract_id}")
async def get_single_consistency_check(
    contract_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取单个合同一致性校验结果（只读）。"""
    issues = await check_contract_consistency(db, contract_id)
    return {"contract_id": contract_id, "issues": issues}


@router.post("/consistency-check/refresh")
async def refresh_consistency_check(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """重新计算并返回最新一致性校验结果（不持久化）。"""
    return await check_all_contracts_consistency(db)
