"""v1.9 项目粗利润 API 路由。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.core.profit_utils import (
    calculate_project_profit_v19,
    refresh_project_profit_cache,
    get_profit_overview,
)

router = APIRouter()


@router.get("/{project_id}/profit")
async def get_project_profit(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取项目粗利润报告（实时计算）。"""
    result = await calculate_project_profit_v19(db, project_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail="项目不存在")
    return result


@router.post("/{project_id}/profit/refresh")
async def refresh_profit(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """刷新项目粗利润缓存。"""
    result = await refresh_project_profit_cache(db, project_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail="项目不存在")
    return result
