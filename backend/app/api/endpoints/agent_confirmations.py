"""v2.0 AI Agent 闭环——建议确认与动作执行 API。"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.agent_action import AgentAction
from app.models.human_confirmation import HumanConfirmation

router = APIRouter()


class ConfirmRequest(BaseModel):
    decision_type: str
    reason_code: Optional[str] = None
    free_text_reason: Optional[str] = None
    corrected_fields: Optional[dict] = None
    user_priority_override: Optional[str] = None


@router.post("/suggestions/{suggestion_id}/confirm")
async def confirm_suggestion(
    suggestion_id: int,
    body: ConfirmRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """确认/拒绝 Agent 建议。"""
    from app.core.agent_actions_service import confirm_suggestion as _confirm
    result = await _confirm(
        db,
        suggestion_id=suggestion_id,
        decision_type=body.decision_type,
        reason_code=body.reason_code,
        free_text_reason=body.free_text_reason,
        corrected_fields=body.corrected_fields,
        user_priority_override=body.user_priority_override,
    )
    return {"code": 0, "data": result}


@router.get("/actions")
async def list_agent_actions(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    action_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查询 Agent 动作列表。"""
    query = select(AgentAction)
    if action_type:
        query = query.where(AgentAction.action_type == action_type)
    if status:
        query = query.where(AgentAction.status == status)
    query = query.order_by(AgentAction.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()
    return {"code": 0, "data": [
        {
            "id": a.id,
            "suggestion_id": a.suggestion_id,
            "action_type": a.action_type,
            "status": a.status,
            "result": a.result,
            "error_message": a.error_message,
            "executed_at": a.executed_at.isoformat() if a.executed_at else None,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in items
    ]}


@router.get("/actions/{action_id}")
async def get_agent_action(
    action_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查询 Agent 动作详情。"""
    result = await db.execute(
        select(AgentAction).where(AgentAction.id == action_id)
    )
    action = result.scalar_one_or_none()
    if not action:
        from app.core.exception_handlers import BusinessException
        from app.core.error_codes import ERROR_CODES
        raise BusinessException(
            status_code=400,
            detail=ERROR_CODES.get("NOT_FOUND", "记录不存在"),
            code="NOT_FOUND",
        )
    return {"code": 0, "data": {
        "id": action.id,
        "suggestion_id": action.suggestion_id,
        "action_type": action.action_type,
        "action_params": action.action_params,
        "status": action.status,
        "result": action.result,
        "error_message": action.error_message,
        "executed_at": action.executed_at.isoformat() if action.executed_at else None,
        "created_at": action.created_at.isoformat() if action.created_at else None,
    }}
