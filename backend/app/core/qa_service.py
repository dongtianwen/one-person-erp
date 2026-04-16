"""v2.1 经营数据自由问答服务。

仅 LLM_PROVIDER=api 可用。前端维护对话历史，后端不落库。
"""
import json
import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.constants import (
    QA_CONTEXT_MONTHS,
    QA_CONTEXT_MAX_PROJECTS,
    QA_MAX_HISTORY_TURNS,
    LLM_PROVIDER_API,
)
from app.core.error_codes import ERROR_CODES
from app.core.exception_handlers import BusinessException
from app.core.llm_client import get_llm_provider, ExternalAPIProvider

logger = logging.getLogger(__name__)

QA_SYSTEM_PROMPT = (
    "你是一人公司经营助手。\n"
    "以下是当前经营数据（JSON 格式），请基于这些真实数据回答用户的问题。\n\n"
    "经营数据：\n{context_json}\n\n"
    "回答要求：\n"
    "1. 只基于以上数据回答，不要编造数据\n"
    "2. 回答简洁，重点突出，适合一人公司老板快速决策\n"
    "3. 如果数据不足以回答问题，明确说明缺少哪些信息\n"
    "4. 使用中文回答"
)


async def build_qa_context(db: AsyncSession) -> Dict[str, Any]:
    """构建固定经营数据包。"""
    context: Dict[str, Any] = {}
    all_failed = True

    try:
        context["finance_summary"] = await _build_finance_summary(db)
        all_failed = False
    except Exception as e:
        logger.warning("QA context: 财务摘要构建失败: %s", e)
        context["finance_summary"] = None

    try:
        context["active_projects"] = await _build_active_projects(db)
        all_failed = False
    except Exception as e:
        logger.warning("QA context: 活跃项目构建失败: %s", e)
        context["active_projects"] = None

    try:
        context["overdue_contracts"] = await _build_overdue_contracts(db)
        all_failed = False
    except Exception as e:
        logger.warning("QA context: 逾期合同构建失败: %s", e)
        context["overdue_contracts"] = None

    context["today"] = date.today().isoformat()

    if all_failed:
        raise BusinessException(
            status_code=500,
            detail=ERROR_CODES["QA_CONTEXT_BUILD_FAILED"],
            code="QA_CONTEXT_BUILD_FAILED",
        )

    return context


async def _build_finance_summary(db: AsyncSession) -> List[Dict[str, Any]]:
    """构建近 N 个月财务摘要。"""
    from app.models.finance import FinanceRecord

    months = QA_CONTEXT_MONTHS
    today = date.today()
    start_date = today.replace(day=1) - timedelta(days=30 * (months - 1))

    result = await db.execute(
        select(
            func.strftime("%Y-%m", FinanceRecord.date).label("month"),
            func.sum(
                case((FinanceRecord.type == "income", FinanceRecord.amount), else_=0)
            ).label("income"),
            func.sum(
                case((FinanceRecord.type == "expense", FinanceRecord.amount), else_=0)
            ).label("expense"),
        )
        .where(FinanceRecord.date >= start_date, FinanceRecord.is_deleted == False)
        .group_by("month")
        .order_by("month")
    )

    summary = []
    for row in result.all():
        income = float(row.income or 0)
        expense = float(row.expense or 0)
        gross_rate = (income - expense) / income * 100 if income > 0 else 0
        summary.append({
            "month": row.month,
            "income": round(income, 2),
            "expense": round(expense, 2),
            "gross_margin_rate": round(gross_rate, 1),
        })

    pending_result = await db.execute(
        select(func.sum(FinanceRecord.amount)).where(
            FinanceRecord.type == "income",
            FinanceRecord.status != "received",
            FinanceRecord.is_deleted == False,
        )
    )
    pending = float(pending_result.scalar() or 0)

    return {"monthly": summary, "pending_receipt": round(pending, 2)}


async def _build_active_projects(db: AsyncSession) -> List[Dict[str, Any]]:
    """构建活跃项目列表。"""
    from app.models.project import Project

    result = await db.execute(
        select(Project)
        .options(selectinload(Project.customer))
        .where(
            Project.status.in_(["in_progress", "not_started"]),
            Project.is_deleted == False,
        )
        .order_by(Project.created_at.desc())
        .limit(QA_CONTEXT_MAX_PROJECTS)
    )
    projects = result.scalars().all()

    items = []
    for p in projects:
        # 兼容当前项目模型字段，避免依赖未落地的缓存列。
        contract_amount = float(getattr(p, "contract_amount", None) or p.budget or 0)
        received = await _get_project_received(db, p.id)
        items.append({
            "project_name": p.name,
            "customer_name": p.customer.name if p.customer else "",
            "start_date": p.start_date.isoformat() if p.start_date else None,
            "contract_amount": contract_amount,
            "milestone_completion_rate": float(
                getattr(p, "cached_completion_rate", None) or p.progress or 0
            ),
            "pending_amount": round(contract_amount - received, 2),
        })
    return items


async def _get_project_received(db: AsyncSession, project_id: int) -> float:
    """获取项目已收款金额。"""
    from app.models.project import Milestone

    result = await db.execute(
        select(func.sum(Milestone.payment_amount)).where(
            Milestone.project_id == project_id,
            Milestone.payment_status == "received",
            Milestone.is_deleted == False,
        )
    )
    return float(result.scalar() or 0)


async def _build_overdue_contracts(db: AsyncSession) -> List[Dict[str, Any]]:
    """构建逾期合同列表。"""
    from app.models.contract import Contract

    today = date.today().isoformat()
    result = await db.execute(
        select(Contract)
        .options(selectinload(Contract.customer))
        .where(
            Contract.end_date < today,
            Contract.status.in_(["active", "signed"]),
            Contract.is_deleted == False,
        )
    )
    contracts = result.scalars().all()

    return [
        {
            "contract_title": c.title,
            "customer_name": c.customer.name if c.customer else "",
            "end_date": c.end_date.isoformat() if c.end_date else None,
            "amount": float(c.amount or 0),
        }
        for c in contracts
    ]


async def ask_question(
    db: AsyncSession,
    question: str,
    history: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """回答经营问题。"""
    from app.models.setting import SystemSetting

    result = await db.execute(select(SystemSetting).where(SystemSetting.key == "agent_config"))
    db_setting = result.scalar_one_or_none()
    agent_config = None
    if db_setting and db_setting.value:
        agent_config = json.loads(db_setting.value)

    provider = get_llm_provider(agent_config)
    if not isinstance(provider, ExternalAPIProvider):
        raise BusinessException(
            status_code=403,
            detail=ERROR_CODES["QA_REQUIRES_API_PROVIDER"],
            code="QA_REQUIRES_API_PROVIDER",
        )

    if not provider.is_available():
        raise BusinessException(
            status_code=503,
            detail=ERROR_CODES.get("API_PROVIDER_UNAVAILABLE", "外部 API 不可用"),
            code="API_PROVIDER_UNAVAILABLE",
        )

    context = await build_qa_context(db)
    context_json = json.dumps(context, ensure_ascii=False, default=str)
    system_msg = QA_SYSTEM_PROMPT.format(context_json=context_json)

    messages = [{"role": "system", "content": system_msg}]

    if history:
        truncated = history[-QA_MAX_HISTORY_TURNS * 2:]
        messages.extend(truncated)

    messages.append({"role": "user", "content": question})

    answer = await provider.call_freeform(messages)
    if not answer:
        raise BusinessException(
            status_code=503,
            detail=ERROR_CODES.get("API_PROVIDER_UNAVAILABLE", "外部 API 不可用"),
            code="API_PROVIDER_UNAVAILABLE",
        )
    return {
        "answer": answer or "",
        "llm_model": provider.get_model_name(),
    }
