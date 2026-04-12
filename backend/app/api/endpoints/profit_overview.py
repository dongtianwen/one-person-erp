"""v1.9 粗利润概览 API 路由（finance 层级）。"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.core.profit_utils import get_profit_overview

router = APIRouter()


@router.get("/profit-overview")
async def list_profit_overview(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取所有项目粗利润概览。"""
    return await get_profit_overview(db)
