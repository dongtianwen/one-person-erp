"""v2.0 AI Agent 闭环——Agent 运行核心服务。"""
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    AGENT_TYPE_BUSINESS_DECISION,
    AGENT_TYPE_PROJECT_MANAGEMENT,
    AGENT_TYPE_DELIVERY_QC,
    AGENT_RUN_STATUS_WHITELIST,
    AGENT_TRIGGER_TYPE_WHITELIST,
    LLM_PROVIDER_NONE,
    LLM_PROVIDER_LOCAL,
    LLM_PROVIDER_API,
    SUGGESTION_STATUS_WHITELIST,
)
from app.core.exception_handlers import BusinessException
from app.core.agent_rules import (
    run_business_decision_rules,
    run_project_management_rules,
    run_delivery_qc_rules,
)
from app.core.llm_client import get_llm_provider, build_llm_context

logger = logging.getLogger(__name__)


async def run_agent(
    db: AsyncSession,
    agent_type: str,
    trigger_type: str = "manual",
    project_id: Optional[int] = None,
    package_id: Optional[int] = None,
    use_llm: bool = True,
) -> Dict[str, Any]:
    """运行 Agent 核心函数。

    1. 执行规则引擎
    2. 尝试 LLM 增强
    3. 持久化运行记录和建议
    """
    from app.models.agent_run import AgentRun
    from app.models.agent_suggestion import AgentSuggestion

    valid_types = [AGENT_TYPE_BUSINESS_DECISION, AGENT_TYPE_PROJECT_MANAGEMENT, AGENT_TYPE_DELIVERY_QC]
    if agent_type not in valid_types:
        raise BusinessException(
            status_code=400,
            detail=f"不支持的 agent_type: {agent_type}",
            code="INVALID_PARAM",
        )

    if trigger_type not in AGENT_TRIGGER_TYPE_WHITELIST:
        raise BusinessException(
            status_code=400,
            detail=f"不支持的 trigger_type: {trigger_type}",
            code="INVALID_PARAM",
        )

    # 0. 加载 AI 配置（从数据库读取，覆盖 .env）
    from app.models.setting import SystemSetting
    result = await db.execute(select(SystemSetting).where(SystemSetting.key == "agent_config"))
    db_setting = result.scalar_one_or_none()
    
    agent_config = None
    if db_setting and db_setting.value:
        try:
            agent_config = json.loads(db_setting.value)
        except Exception:
            pass

    llm_provider = get_llm_provider(agent_config)
    provider_name = llm_provider.get_model_name() if llm_provider else "none"

    run_record = AgentRun(
        agent_type=agent_type,
        trigger_type=trigger_type,
        status="running",
        llm_provider=provider_name.split(":")[0] if ":" in provider_name else provider_name,
        llm_enhanced=False,
        llm_model=provider_name,
    )
    db.add(run_record)
    await db.flush()

    try:
        # 1. 执行规则引擎
        if agent_type == AGENT_TYPE_BUSINESS_DECISION:
            rules_output = await run_business_decision_rules(db)
        elif agent_type == AGENT_TYPE_PROJECT_MANAGEMENT:
            rules_output = await run_project_management_rules(db, project_id)
        elif agent_type == AGENT_TYPE_DELIVERY_QC:
            rules_output = await run_delivery_qc_rules(db, package_id)
        else:
            rules_output = []

        run_record.rule_output = json.dumps(rules_output, ensure_ascii=False) if rules_output else None

        # 2. 尝试 LLM 增强（仅在 use_llm=True 时）
        llm_enhanced = False
        if use_llm:
            all_suggestions = list(rules_output) if rules_output else []

            if all_suggestions:
                ctx = build_llm_context(all_suggestions)
                enhanced = await llm_provider.enhance(ctx["rule_text"], ctx["feedback_text"])
                if enhanced:
                    llm_enhanced = True
                    run_record.llm_enhanced = True
                    enhanced_map = {e.get("index"): e for e in enhanced if "index" in e}
                    for i, item in enumerate(all_suggestions):
                        e_item = enhanced_map.get(i)
                        if e_item:
                            item["title"] = e_item.get("title", item["title"])
                            item["description"] = e_item.get("description", item["description"])
                            item["llm_enhanced"] = 1
                        elif i < len(enhanced) and len(enhanced) == len(all_suggestions) and not enhanced_map:
                            item["title"] = enhanced[i].get("title", item["title"])
                            item["description"] = enhanced[i].get("description", item["description"])
                            item["llm_enhanced"] = 1

            # rules_output 只保留本次规则输出的部分
            if rules_output:
                rules_output = all_suggestions[:len(rules_output)]

        # 3. 持久化建议（每次运行都创建全新建议，旧 pending 建议标记为 superseded）
        if rules_output:
            result = await db.execute(
                select(AgentSuggestion).where(
                    AgentSuggestion.agent_run_id.in_(
                        select(AgentRun.id).where(AgentRun.agent_type == agent_type)
                    ),
                )
            )
            for s in result.scalars():
                if s.status == "pending":
                    s.status = "superseded"

        for item in rules_output:
            suggestion = AgentSuggestion(
                agent_run_id=run_record.id,
                decision_type=item["decision_type"],
                suggestion_type=item["suggestion_type"],
                title=item["title"],
                description=item["description"],
                priority=item.get("priority", "medium"),
                status="pending",
                suggested_action=item.get("suggested_action", "none"),
                action_params=item.get("action_params"),
                source_rule=item.get("source_rule", ""),
                llm_enhanced=item.get("llm_enhanced", 0),
                risk_score=item.get("risk_score", 0),
                strategy_code=item.get("strategy_code", ""),
                score_breakdown=item.get("score_breakdown"),
            )
            db.add(suggestion)

        # 4. 标记运行完成
        run_record.status = "completed"
        run_record.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)

        await db.commit()

        logger.info(
            "Agent 运行完成 | type=%s | trigger=%s | suggestions=%d | llm=%s",
            agent_type, trigger_type, len(rules_output), provider_name,
        )

        return {
            "run_id": run_record.id,
            "agent_type": agent_type,
            "status": "completed",
            "suggestion_count": len(rules_output),
            "llm_provider": provider_name,
            "llm_enhanced": llm_enhanced,
        }

    except Exception as e:
        run_record.status = "failed"
        run_record.error_message = str(e)
        await db.commit()
        logger.error("Agent 运行失败 | type=%s | error=%s", agent_type, e)
        raise BusinessException(
            status_code=500,
            detail=f"Agent 运行失败: {e}",
            code="ACTION_EXECUTION_FAILED",
        )
