"""v1.9 固定成本 CRUD API 路由。"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.fixed_cost import FixedCost
from app.core.constants import (
    FIXED_COST_PERIOD_WHITELIST,
    FIXED_COST_CATEGORY_WHITELIST,
)
from app.core.fixed_cost_utils import (
    validate_fixed_cost_dates,
    get_monthly_fixed_costs,
    get_project_fixed_costs_total,
)

router = APIRouter()


@router.post("")
async def create_fixed_cost(
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建固定成本条目。"""
    amount = data.get("amount", 0)
    if amount <= 0:
        raise HTTPException(status_code=422, detail="金额必须大于 0")

    period = data.get("period", "monthly")
    if period not in FIXED_COST_PERIOD_WHITELIST:
        raise HTTPException(status_code=422, detail=f"周期必须在 {FIXED_COST_PERIOD_WHITELIST} 内")

    category = data.get("category", "other")
    if category not in FIXED_COST_CATEGORY_WHITELIST:
        raise HTTPException(status_code=422, detail=f"分类必须在 {FIXED_COST_CATEGORY_WHITELIST} 内")

    effective_date = date.fromisoformat(data["effective_date"])
    end_date = date.fromisoformat(data["end_date"]) if data.get("end_date") else None

    if not validate_fixed_cost_dates(effective_date, end_date):
        raise HTTPException(status_code=422, detail="end_date 必须 >= effective_date")

    cost = FixedCost(
        name=data["name"],
        category=category,
        amount=amount,
        period=period,
        effective_date=effective_date,
        end_date=end_date,
        project_id=data.get("project_id"),
        notes=data.get("notes"),
    )
    db.add(cost)
    await db.commit()
    await db.refresh(cost)
    return {"id": cost.id, "message": "创建成功"}


@router.get("")
async def list_fixed_costs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取所有固定成本条目。"""
    stmt = select(FixedCost).order_by(FixedCost.effective_date.desc())
    result = await db.execute(stmt)
    costs = result.scalars().all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "category": c.category,
            "amount": float(c.amount),
            "period": c.period,
            "effective_date": c.effective_date.isoformat(),
            "end_date": c.end_date.isoformat() if c.end_date else None,
            "project_id": c.project_id,
            "notes": c.notes,
        }
        for c in costs
    ]


@router.get("/summary")
async def get_fixed_costs_summary(
    period: str = Query(..., description="会计期间 YYYY-MM"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取指定月份固定成本汇总。"""
    return await get_monthly_fixed_costs(db, period)


@router.get("/{cost_id}")
async def get_fixed_cost(
    cost_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取单个固定成本详情。"""
    stmt = select(FixedCost).where(FixedCost.id == cost_id)
    result = await db.execute(stmt)
    cost = result.scalar_one_or_none()
    if not cost:
        raise HTTPException(status_code=404, detail="固定成本不存在")
    return {
        "id": cost.id,
        "name": cost.name,
        "category": cost.category,
        "amount": float(cost.amount),
        "period": cost.period,
        "effective_date": cost.effective_date.isoformat(),
        "end_date": cost.end_date.isoformat() if cost.end_date else None,
        "project_id": cost.project_id,
        "notes": cost.notes,
    }


@router.put("/{cost_id}")
async def update_fixed_cost(
    cost_id: int,
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新固定成本条目。"""
    stmt = select(FixedCost).where(FixedCost.id == cost_id)
    result = await db.execute(stmt)
    cost = result.scalar_one_or_none()
    if not cost:
        raise HTTPException(status_code=404, detail="固定成本不存在")

    if "name" in data:
        cost.name = data["name"]
    if "category" in data:
        if data["category"] not in FIXED_COST_CATEGORY_WHITELIST:
            raise HTTPException(status_code=422, detail="分类不合法")
        cost.category = data["category"]
    if "amount" in data:
        if data["amount"] <= 0:
            raise HTTPException(status_code=422, detail="金额必须大于 0")
        cost.amount = data["amount"]
    if "period" in data:
        if data["period"] not in FIXED_COST_PERIOD_WHITELIST:
            raise HTTPException(status_code=422, detail="周期不合法")
        cost.period = data["period"]
    if "effective_date" in data:
        cost.effective_date = date.fromisoformat(data["effective_date"])
    if "end_date" in data:
        cost.end_date = date.fromisoformat(data["end_date"]) if data["end_date"] else None
    if "project_id" in data:
        cost.project_id = data["project_id"]
    if "notes" in data:
        cost.notes = data["notes"]

    if not validate_fixed_cost_dates(cost.effective_date, cost.end_date):
        raise HTTPException(status_code=422, detail="end_date 必须 >= effective_date")

    await db.commit()
    return {"message": "更新成功"}


@router.delete("/{cost_id}")
async def delete_fixed_cost(
    cost_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除固定成本条目。"""
    stmt = select(FixedCost).where(FixedCost.id == cost_id)
    result = await db.execute(stmt)
    cost = result.scalar_one_or_none()
    if not cost:
        raise HTTPException(status_code=404, detail="固定成本不存在")
    await db.delete(cost)
    await db.commit()
    return {"message": "删除成功"}
