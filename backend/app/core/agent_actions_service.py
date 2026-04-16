"""v2.0 AI Agent 闭环——建议确认与动作执行服务。"""
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    ACTION_TYPE_CREATE_TODO,
    ACTION_TYPE_CREATE_REMINDER,
    ACTION_TYPE_GENERATE_REPORT,
    DECISION_TYPE_WHITELIST,
    PRIORITY_WHITELIST,
)
from app.core.error_codes import ERROR_CODES
from app.core.exception_handlers import BusinessException

logger = logging.getLogger(__name__)


async def confirm_suggestion(
    db: AsyncSession,
    suggestion_id: int,
    decision_type: str,
    reason_code: Optional[str] = None,
    free_text_reason: Optional[str] = None,
    corrected_fields: Optional[dict] = None,
    user_priority_override: Optional[str] = None,
) -> Dict[str, Any]:
    """确认/拒绝建议。

    1. 校验建议状态
    2. 记录人工确认
    3. 如果接受，创建并执行对应动作
    """
    from app.models.agent_suggestion import AgentSuggestion
    from app.models.human_confirmation import HumanConfirmation
    from app.models.agent_action import AgentAction

    result = await db.execute(
        select(AgentSuggestion).where(AgentSuggestion.id == suggestion_id)
    )
    suggestion = result.scalar_one_or_none()
    if not suggestion:
        raise BusinessException(
            status_code=400,
            detail=ERROR_CODES.get("NOT_FOUND", "记录不存在"),
            code="NOT_FOUND",
        )
    if suggestion.status != "pending":
        raise BusinessException(
            status_code=400,
            detail="建议已确认",
            code="SUGGESTION_NOT_PENDING",
        )
    if decision_type not in DECISION_TYPE_WHITELIST:
        raise BusinessException(
            status_code=400,
            detail=f"不支持的决策类型: {decision_type}",
            code="INVALID_PARAM",
        )

    # 1. 更新建议状态
    suggestion.status = "confirmed" if decision_type == "accepted" else "rejected"

    # 2. 记录确认
    confirmation = HumanConfirmation(
        suggestion_id=suggestion_id,
        decision_type=decision_type,
        reason_code=reason_code,
        free_text_reason=free_text_reason,
        corrected_fields=json.dumps(corrected_fields) if corrected_fields else None,
        user_priority_override=user_priority_override,
    )
    db.add(confirmation)

    # 3. 如果接受，创建动作
    action_result = None
    if decision_type == "accepted":
        action = await _execute_action(db, suggestion)
        action_result = {"action_id": action.id, "action_type": action.action_type, "status": action.status}

    await db.commit()

    return {
        "suggestion_id": suggestion_id,
        "decision_type": decision_type,
        "action": action_result,
    }


async def _execute_action(db: AsyncSession, suggestion: Any) -> Any:
    """根据建议创建并执行动作。"""
    from app.models.agent_action import AgentAction
    from app.models.todo import Todo
    from app.models.agent_suggestion import AgentSuggestion

    action_type = suggestion.suggested_action or "none"
    action_params = {}
    if suggestion.action_params:
        try:
            action_params = json.loads(suggestion.action_params)
        except json.JSONDecodeError:
            action_params = {}

    # 创建动作记录
    action = AgentAction(
        suggestion_id=suggestion.id,
        action_type=action_type,
        action_params=suggestion.action_params,
        status="pending",
    )
    db.add(action)
    await db.flush()

    if action_type == ACTION_TYPE_CREATE_TODO:
        todo = Todo(
            title=action_params.get("action", suggestion.title),
            description=suggestion.description,
            priority=suggestion.priority,
            status="pending",
            source="agent",
            source_id=suggestion.id,
        )
        if "due_date" in action_params:
            todo.due_date = action_params["due_date"]
        db.add(todo)
        await db.flush()
        action.status = "executed"
        action.result = json.dumps({"todo_id": todo.id})
    elif action_type == ACTION_TYPE_CREATE_REMINDER:
        action.status = "executed"
        action.result = json.dumps({"message": "reminder_created", "data": action_params})
    elif action_type == ACTION_TYPE_GENERATE_REPORT:
        action.status = "executed"
        action.result = json.dumps({"message": "report_generated", "data": action_params})
    else:
        action.status = "executed"
        action.result = json.dumps({"message": "no_action_needed"})

    action.executed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    logger.info("动作执行完成 | action_id=%d | type=%s | status=%s", action.id, action.action_type, action.status)
    return action
