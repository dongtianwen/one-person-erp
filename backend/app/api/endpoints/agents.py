"""v2.0 AI Agent 闭环——Agent 运行 API。"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.agent_run import AgentRun
from app.models.agent_suggestion import AgentSuggestion
from app.models.setting import SystemSetting
from app.core.exception_handlers import BusinessException
from app.core.error_codes import ERROR_CODES

router = APIRouter()


@router.post("/business-decision/run")
async def run_business_decision(
    use_llm: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """经营决策 Agent——扫描全局业务数据，生成建议。"""
    from app.core.agent_service import run_agent
    result = await run_agent(db, agent_type="business_decision", trigger_type="manual", use_llm=use_llm)
    return {"code": 0, "data": result}


@router.post("/project-management/run")
async def run_project_management(
    project_id: Optional[int] = Query(None, description="指定项目ID，不传则扫描全部项目"),
    use_llm: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """项目管理 Agent——扫描项目数据，生成建议。"""
    from app.core.agent_service import run_agent
    result = await run_agent(db, agent_type="project_management", trigger_type="manual", use_llm=use_llm, project_id=project_id)
    return {"code": 0, "data": result}


@router.post("/delivery-qc/run")
async def run_delivery_qc(
    package_id: int = Query(..., description="交付包ID"),
    use_llm: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """交付/质检 Agent——检查交付包完整性，生成建议。"""
    from app.core.agent_service import run_agent
    result = await run_agent(db, agent_type="delivery_qc", trigger_type="manual", use_llm=use_llm, package_id=package_id)
    return {"code": 0, "data": result}


@router.get("/runs")
async def list_agent_runs(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    agent_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查询 Agent 运行记录列表。"""
    query = select(AgentRun).where(AgentRun.is_deleted == False)
    if agent_type:
        query = query.where(AgentRun.agent_type == agent_type)
    if status:
        query = query.where(AgentRun.status == status)
    query = query.order_by(AgentRun.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()

    # 批量查询每个 run 的建议数量，避免 lazy load
    run_ids = [r.id for r in items]
    counts = {}
    if run_ids:
        count_query = select(
            AgentSuggestion.agent_run_id, func.count(AgentSuggestion.id)
        ).where(
            AgentSuggestion.agent_run_id.in_(run_ids),
        ).group_by(AgentSuggestion.agent_run_id)
        count_result = await db.execute(count_query)
        for row in count_result.all():
            counts[row[0]] = row[1]

    return {"code": 0, "data": [
        {
            "id": r.id,
            "agent_type": r.agent_type,
            "trigger_type": r.trigger_type,
            "status": r.status,
            "llm_provider": r.llm_provider,
            "llm_enhanced": r.llm_enhanced,
            "llm_model": r.llm_model,
            "suggestion_count": counts.get(r.id, 0),
            "error_message": r.error_message,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        }
        for r in items
    ]}


@router.get("/runs/{run_id}")
async def get_agent_run(
    run_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查询 Agent 运行详情（含建议列表）。"""
    query = select(AgentRun).where(
        AgentRun.id == run_id, AgentRun.is_deleted == False
    ).options(selectinload(AgentRun.suggestions))
    result = await db.execute(query)
    run = result.scalar_one_or_none()
    if not run:
        raise BusinessException(
            status_code=400,
            detail=ERROR_CODES.get("NOT_FOUND", "记录不存在"),
            code="NOT_FOUND",
        )
    return {"code": 0, "data": {
        "id": run.id,
        "agent_type": run.agent_type,
        "trigger_type": run.trigger_type,
        "status": run.status,
        "llm_provider": run.llm_provider,
        "llm_enhanced": run.llm_enhanced,
        "llm_model": run.llm_model,
        "rule_output": run.rule_output,
        "error_message": run.error_message,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "suggestions": [
            {
                "id": s.id,
                "decision_type": s.decision_type,
                "suggestion_type": s.suggestion_type,
                "title": s.title,
                "description": s.description,
                "priority": s.priority,
                "status": s.status,
                "suggested_action": s.suggested_action,
                "source_rule": s.source_rule,
                "llm_enhanced": s.llm_enhanced,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in run.suggestions
        ],
    }}


@router.get("/suggestions/pending")
async def list_pending_suggestions(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    suggestion_type: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    agent_type: Optional[str] = Query(None, description="Agent类型过滤"),
    deduplicate: bool = Query(True, description="按类型去重，只显示最新的一条"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查询所有待确认的建议。"""
    # 需要 join agent_runs 来过滤 agent_type
    query = select(AgentSuggestion).where(
        AgentSuggestion.status == "pending",
    )
    if agent_type:
        query = query.join(AgentRun, AgentSuggestion.agent_run_id == AgentRun.id).where(
            AgentRun.agent_type == agent_type
        )
    if suggestion_type:
        query = query.where(AgentSuggestion.suggestion_type == suggestion_type)
    if priority:
        query = query.where(AgentSuggestion.priority == priority)

    query = query.order_by(
        AgentSuggestion.priority.asc(),
        AgentSuggestion.created_at.desc(),
    )
    result = await db.execute(query)
    items = result.scalars().all()

    # Python 端去重：按 suggestion_type 保留最新的一条
    if deduplicate:
        seen = {}
        deduped_items = []
        for item in items:
            key = item.suggestion_type
            if key not in seen:
                seen[key] = True
                deduped_items.append(item)
        items = deduped_items

    # 应用分页
    items = items[skip:skip + limit]

    return {"code": 0, "data": [
        {
            "id": s.id,
            "agent_run_id": s.agent_run_id,
            "decision_type": s.decision_type,
            "suggestion_type": s.suggestion_type,
            "title": s.title,
            "description": s.description,
            "priority": s.priority,
            "status": s.status,
            "suggested_action": s.suggested_action,
            "action_params": s.action_params,
            "source_rule": s.source_rule,
            "llm_enhanced": s.llm_enhanced,
            "risk_score": s.risk_score,
            "strategy_code": s.strategy_code,
            "score_breakdown": s.score_breakdown,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in items
    ]}
@router.get("/ollama-models")
async def list_ollama_models(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """探测本地已拉取的模型列表。"""
    import httpx
    import json
    try:
        from app.config import settings
        result = await db.execute(select(SystemSetting).where(SystemSetting.key == "agent_config"))
        db_setting = result.scalar_one_or_none()
        db_config = json.loads(db_setting.value) if db_setting and db_setting.value else {}
        
        # 净化地址：显式使用 127.0.0.1 避开 Windows 解析坑
        raw_url = db_config.get("local_base_url") or settings.LLM_LOCAL_BASE_URL
        base_url = raw_url.strip().replace("localhost", "127.0.0.1")
        
        if not base_url.startswith("http"):
            base_url = f"http://{base_url}"
        
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{base_url.rstrip('/')}/api/tags")
            if resp.status_code == 200:
                data = resp.json()
                models = [m["name"] for m in data.get("models", [])]
                return {"code": 0, "data": models}
            
            # 如果是非 200 响应，抛出异常以便前端捕获捕获详细描述
            logger.warning("Ollama 响应异常 | status=%s", resp.status_code)
            raise Exception(f"服务响应异常 (HTTP {resp.status_code})")
            
    except Exception as e:
        logger.error("探测 Ollama 失败: %s", e)
        # 抛出具体的业务异常，让前端全局拦截器显示详细错误
        raise BusinessException(
            status_code=400,
            detail=f"连接本地 Ollama 失败: {str(e)}。请确保服务在 {base_url} 已启动。",
            code="CONNECTION_ERROR"
        )


@router.get("/config")
async def get_agent_config(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取 Agent AI 配置。"""
    from app.config import settings
    
    # 尝试从数据库读取
    result = await db.execute(select(SystemSetting).where(SystemSetting.key == "agent_config"))
    db_setting = result.scalar_one_or_none()
    
    import json
    db_config = json.loads(db_setting.value) if db_setting and db_setting.value else {}
    
    # 合并环境变量作为默认值
    config = {
        "provider": db_config.get("provider") or settings.LLM_PROVIDER,
        "local_model": db_config.get("local_model") or settings.LLM_LOCAL_MODEL,
        "local_base_url": db_config.get("local_base_url") or settings.LLM_LOCAL_BASE_URL,
        "api_base": db_config.get("api_base") or settings.LLM_API_BASE,
        "api_key": db_config.get("api_key") or settings.LLM_API_KEY,
        "api_model": db_config.get("api_model") or settings.LLM_API_MODEL,
    }
    return {"code": 0, "data": config}


@router.post("/config")
async def update_agent_config(
    config: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新 Agent AI 配置。"""
    import json
    value_str = json.dumps(config, ensure_ascii=False)
    
    result = await db.execute(select(SystemSetting).where(SystemSetting.key == "agent_config"))
    db_setting = result.scalar_one_or_none()
    
    if db_setting:
        db_setting.value = value_str
    else:
        new_setting = SystemSetting(key="agent_config", value=value_str)
        db.add(new_setting)
    
    await db.commit()
    return {"code": 0, "message": "配置已保存"}
