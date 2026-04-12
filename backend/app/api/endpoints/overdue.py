"""v1.9 收款逾期预警 API 路由。"""

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.core.overdue_utils import (
    get_overdue_milestones,
    get_customer_risk_summary,
    refresh_customer_risk_fields,
)

router = APIRouter()


@router.get("/overdue-warnings")
async def get_overdue_warnings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取逾期预警报告（只读）。"""
    overdue = await get_overdue_milestones(db)

    # 按客户聚合风险摘要
    customer_map: dict[int, dict] = {}
    for m in overdue:
        cid = m["customer_id"]
        if cid not in customer_map:
            customer_map[cid] = {
                "customer_id": cid,
                "customer_name": m["customer_name"],
                "overdue_count": 0,
                "overdue_amount": 0.0,
            }
        customer_map[cid]["overdue_count"] += 1
        customer_map[cid]["overdue_amount"] += m["payment_amount"]

    return {
        "checked_at": datetime.utcnow().isoformat(),
        "overdue_milestones": overdue,
        "customer_risk_summary": list(customer_map.values()),
    }


@router.get("/overdue-warnings/{customer_id}")
async def get_customer_risk(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取单个客户风险摘要。"""
    return await get_customer_risk_summary(db, customer_id)


@router.post("/overdue-warnings/refresh")
async def refresh_overdue_warnings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """批量刷新客户风险字段（写入 customers 表）。"""
    count = await refresh_customer_risk_fields(db)
    return {"updated_count": count}
