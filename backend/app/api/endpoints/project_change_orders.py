"""FR-505 项目维度变更单摘要（只读）——挂载在 /api/v1/projects/{project_id}/change-orders"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.contract import Contract
from app.models.change_order import ChangeOrder
from app.schemas.change_order import ChangeOrderSummaryItem

router = APIRouter()


@router.get("/summary", response_model=list[ChangeOrderSummaryItem])
async def project_change_order_summary(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """项目维度变更单摘要（只读，职责分离）。展示关联合同的变更单，无写操作"""
    project = await db.get(Project, project_id)
    if not project or project.is_deleted:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 查找该项目所有关联合同
    contracts_result = await db.execute(
        select(Contract.id, Contract.contract_no).where(
            Contract.project_id == project_id,
            Contract.is_deleted == False,
        )
    )
    contracts = {cid: cno for cid, cno in contracts_result.all()}

    if not contracts:
        return []

    # 查找这些合同的所有变更单
    orders_result = await db.execute(
        select(ChangeOrder)
        .where(ChangeOrder.contract_id.in_(contracts.keys()))
        .order_by(ChangeOrder.created_at.desc())
    )
    orders = list(orders_result.scalars().all())

    return [
        ChangeOrderSummaryItem(
            order_no=o.order_no,
            title=o.title,
            amount=o.amount,
            status=o.status,
            contract_id=o.contract_id,
            contract_no=contracts.get(o.contract_id),
        )
        for o in orders
    ]
