"""v2.1 深度报告生成服务。

Jinja2 结构渲染 + LLM 分析段落填充，reports 表版本管理。
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from jinja2 import Template
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    REPORT_TYPE_WHITELIST,
    REPORT_TYPE_PROJECT,
    REPORT_TYPE_CUSTOMER,
    REPORT_STATUS_GENERATING,
    REPORT_STATUS_COMPLETED,
    REPORT_STATUS_FAILED,
    PROJECT_REPORT_LLM_VARS,
    CUSTOMER_REPORT_LLM_VARS,
    REPORT_LLM_FALLBACK_TEXT,
)
from app.core.error_codes import ERROR_CODES
from app.core.exception_handlers import BusinessException
from app.core.llm_client import get_llm_provider, ExternalAPIProvider

logger = logging.getLogger(__name__)

REPORT_VAR_PROMPTS = {
    "analysis_summary": "根据以下项目数据，用 2-3 句话总结项目整体执行情况：\n{context_summary}",
    "risk_retrospective": "根据以下项目数据，指出项目中出现的主要风险和问题：\n{context_summary}",
    "improvement_suggestions": "根据以下项目数据，给出 2-3 条具体的改进建议：\n{context_summary}",
    "value_assessment": "根据以下客户数据，评估该客户的商业价值（1-2 句话）：\n{context_summary}",
    "relationship_summary": "根据以下客户数据，描述合作关系特点（1-2 句话）：\n{context_summary}",
    "next_action_suggestions": "根据以下客户数据，给出 1-2 条下一步跟进建议：\n{context_summary}",
}

DEFAULT_REPORT_TEMPLATES = {
    REPORT_TYPE_PROJECT: """项目复盘报告

项目名称：{{ project_name }}
客户名称：{{ customer_name }}
生成日期：{{ generated_date }}

一、项目概况
- 项目周期：{{ start_date }} 至 {{ end_date }}（共 {{ duration_days }} 天）
- 合同金额：{{ contract_amount }}
- 已回款：{{ received_amount }}
- 待回款：{{ pending_amount }}
- 总工时：{{ total_hours }}
- 里程碑完成率：{{ milestone_completion_rate }}%
- 变更次数：{{ change_count }}
- 验收状态：{{ acceptance_passed }}

二、成本与利润
- 直接成本：{{ direct_cost }}
- 外包成本：{{ outsource_cost }}
- 毛利率：{{ gross_margin_rate }}%

三、AI 分析
项目总结：{{ analysis_summary }}
风险复盘：{{ risk_retrospective }}
改进建议：{{ improvement_suggestions }}
""",
    REPORT_TYPE_CUSTOMER: """客户分析报告

客户名称：{{ customer_name }}
生成日期：{{ generated_date }}

一、合作概况
- 项目数量：{{ project_count }}
- 首次合作时间：{{ first_project_date }}
- 最近合作时间：{{ last_project_date }}

二、价值指标
- 合同总额：{{ total_contract_amount }}
- 已回款：{{ total_received_amount }}
- 待回款：{{ total_pending }}
- 预估 LTV：{{ ltv_estimate }}
- 平均项目金额：{{ avg_project_amount }}
- 回款准时率：{{ payment_on_time_rate }}%

三、AI 分析
客户价值：{{ value_assessment }}
合作关系：{{ relationship_summary }}
下一步建议：{{ next_action_suggestions }}
""",
}


async def build_project_report_context(db: AsyncSession, project_id: int) -> Dict[str, Any]:
    """构建项目复盘报告结构性数据。"""
    from app.models.project import Project
    from app.models.project import Milestone, Task

    result = await db.execute(
        select(Project)
        .options(selectinload(Project.customer))
        .where(Project.id == project_id, Project.is_deleted == False)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise BusinessException(
            status_code=404,
            detail=ERROR_CODES["REPORT_ENTITY_NOT_FOUND"],
            code="REPORT_ENTITY_NOT_FOUND",
        )

    contract_amount = float(project.budget or 0)
    received = await _get_project_received(db, project_id)
    total_hours = await _get_project_hours(db, project_id)
    change_count = await _get_change_count(db, project_id)
    acceptance_passed = await _get_acceptance_status(db, project_id)
    direct_cost = await _get_direct_cost(db, project_id)
    outsource_cost = await _get_outsource_cost(db, project_id)
    gross_margin_rate = (
        (contract_amount - direct_cost - outsource_cost) / contract_amount * 100 if contract_amount > 0 else 0
    )

    start = project.start_date
    end = project.end_date
    duration_days = (end - start).days if start and end else 0

    return {
        "project_name": project.name,
        "customer_name": project.customer.name if project.customer else "",
        "generated_date": datetime.now().strftime("%Y-%m-%d"),
        "start_date": start.isoformat() if start else "",
        "end_date": end.isoformat() if end else "",
        "duration_days": duration_days,
        "contract_amount": contract_amount,
        "received_amount": received,
        "pending_amount": max(contract_amount - received, 0),
        "total_hours": total_hours,
        "milestone_completion_rate": float(project.progress or 0),
        "change_count": change_count,
        "acceptance_passed": acceptance_passed,
        "gross_margin_rate": gross_margin_rate,
        "direct_cost": direct_cost,
        "outsource_cost": outsource_cost,
    }


async def build_customer_report_context(db: AsyncSession, customer_id: int) -> Dict[str, Any]:
    """构建客户分析报告结构性数据。"""
    from app.models.customer import Customer
    from app.models.project import Project

    result = await db.execute(select(Customer).where(Customer.id == customer_id, Customer.is_deleted == False))
    customer = result.scalar_one_or_none()
    if not customer:
        raise BusinessException(
            status_code=404,
            detail=ERROR_CODES["REPORT_ENTITY_NOT_FOUND"],
            code="REPORT_ENTITY_NOT_FOUND",
        )

    projects_result = await db.execute(
        select(Project).where(Project.customer_id == customer_id, Project.is_deleted == False)
    )
    projects = projects_result.scalars().all()

    project_count = len(projects)
    total_contract = sum(float(p.budget or 0) for p in projects)
    total_received = sum([await _get_project_received(db, p.id) for p in projects])
    total_pending = max(total_contract - total_received, 0)

    dates = [p.start_date for p in projects if p.start_date]
    first_date = min(dates).isoformat() if dates else ""
    last_date = max(dates).isoformat() if dates else ""

    avg_amount = total_contract / project_count if project_count > 0 else 0
    ltv = total_contract * 1.5
    on_time_rate = await _get_payment_on_time_rate(db, customer_id)

    return {
        "customer_name": customer.name,
        "generated_date": datetime.now().strftime("%Y-%m-%d"),
        "project_count": project_count,
        "total_contract_amount": f"{total_contract:,.2f}",
        "total_received_amount": f"{total_received:,.2f}",
        "total_pending": f"{total_pending:,.2f}",
        "first_project_date": first_date,
        "last_project_date": last_date,
        "ltv_estimate": f"{ltv:,.2f}",
        "avg_project_amount": f"{avg_amount:,.2f}",
        "payment_on_time_rate": f"{on_time_rate:.1f}",
    }


async def fill_llm_vars(
    db: AsyncSession,
    report_type: str,
    context: Dict[str, Any],
) -> Dict[str, str]:
    """逐变量填充 LLM 分析段落，失败降级为 fallback 文本。"""
    var_names = PROJECT_REPORT_LLM_VARS if report_type == REPORT_TYPE_PROJECT else CUSTOMER_REPORT_LLM_VARS

    from app.models.setting import SystemSetting

    result = await db.execute(select(SystemSetting).where(SystemSetting.key == "agent_config"))
    db_setting = result.scalar_one_or_none()
    agent_config = None
    if db_setting and db_setting.value:
        agent_config = json.loads(db_setting.value)

    provider = get_llm_provider(agent_config)
    filled: Dict[str, str] = {}

    if not isinstance(provider, ExternalAPIProvider) or not provider.is_available():
        for var in var_names:
            filled[var] = REPORT_LLM_FALLBACK_TEXT
        return filled

    context_summary = json.dumps(context, ensure_ascii=False, default=str)

    for var in var_names:
        prompt = REPORT_VAR_PROMPTS.get(var, f"请分析 {var}。\n{{context_summary}}")
        prompt = prompt.replace("{context_summary}", context_summary)
        try:
            result = await provider._call_llm_single_var(var, context, prompt)
            filled[var] = result if result else REPORT_LLM_FALLBACK_TEXT
        except Exception as e:
            logger.warning("REPORT_LLM_FILL_FAILED | var=%s | error=%s", var, e)
            filled[var] = REPORT_LLM_FALLBACK_TEXT

    return filled


async def generate_report(
    db: AsyncSession,
    report_type: str,
    entity_id: int,
    template_id: Optional[int] = None,
) -> Dict[str, Any]:
    """生成报告。"""
    from app.models.report import Report
    from app.models.setting import SystemSetting

    if report_type not in REPORT_TYPE_WHITELIST:
        raise BusinessException(
            status_code=400,
            detail=ERROR_CODES["REPORT_TYPE_NOT_SUPPORTED"],
            code="REPORT_TYPE_NOT_SUPPORTED",
        )

    entity_type = "project" if report_type == REPORT_TYPE_PROJECT else "customer"

    result = await db.execute(select(SystemSetting).where(SystemSetting.key == "agent_config"))
    db_setting = result.scalar_one_or_none()
    agent_config = None
    if db_setting and db_setting.value:
        agent_config = json.loads(db_setting.value)

    version_no, parent_id = await _get_next_version(db, report_type, entity_id, entity_type)

    report = Report(
        report_type=report_type,
        entity_id=entity_id,
        entity_type=entity_type,
        template_id=template_id,
        parent_report_id=parent_id,
        version_no=version_no,
        is_latest=1,
        status=REPORT_STATUS_GENERATING,
    )
    db.add(report)
    await db.flush()

    try:
        template_content = await _get_template_content(db, report_type, template_id)
        context = await _build_context(db, report_type, entity_id)
        llm_vars = PROJECT_REPORT_LLM_VARS if report_type == REPORT_TYPE_PROJECT else CUSTOMER_REPORT_LLM_VARS
        llm_filled = await fill_llm_vars(db, report_type, context)
        context.update(llm_filled)

        rendered = Template(template_content).render(**context)

        report.content = rendered
        report.llm_filled_vars = json.dumps(llm_filled, ensure_ascii=False)
        report.status = REPORT_STATUS_COMPLETED
        report.generated_at = datetime.now(timezone.utc).replace(tzinfo=None)

        provider = get_llm_provider(agent_config)
        report.llm_provider = provider.get_model_name().split(":")[0] if provider else "none"
        report.llm_model = provider.get_model_name() if provider else "none"

        await db.commit()

        return {
            "report_id": report.id,
            "status": report.status,
            "content": report.content,
        }

    except Exception as e:
        report.status = REPORT_STATUS_FAILED
        report.error_message = str(e)
        await db.commit()
        logger.error("报告生成失败 | type=%s | entity_id=%d | error=%s", report_type, entity_id, e)
        raise


async def _get_next_version(
    db: AsyncSession,
    report_type: str,
    entity_id: int,
    entity_type: str,
) -> tuple:
    """获取下一个版本号和父报告 ID。"""
    from app.models.report import Report

    result = await db.execute(
        select(Report).where(
            Report.report_type == report_type,
            Report.entity_id == entity_id,
            Report.entity_type == entity_type,
            Report.is_latest == 1,
        )
    )
    latest = result.scalar_one_or_none()

    if latest:
        latest.is_latest = 0
        return latest.version_no + 1, latest.id

    return 1, None


async def _get_template_content(
    db: AsyncSession,
    report_type: str,
    template_id: Optional[int],
) -> str:
    """获取模板内容。"""
    from app.models.template import Template as TemplateModel

    if template_id:
        result = await db.execute(select(TemplateModel).where(TemplateModel.id == template_id))
        tpl = result.scalar_one_or_none()
        if tpl:
            return tpl.content

    result = await db.execute(
        select(TemplateModel).where(TemplateModel.template_type == report_type, TemplateModel.is_default == 1)
    )
    tpl = result.scalar_one_or_none()
    if tpl:
        return tpl.content

    return DEFAULT_REPORT_TEMPLATES.get(report_type, "{{ content }}")


async def _build_context(
    db: AsyncSession,
    report_type: str,
    entity_id: int,
) -> Dict[str, Any]:
    """构建报告上下文。"""
    if report_type == REPORT_TYPE_PROJECT:
        return await build_project_report_context(db, entity_id)
    elif report_type == REPORT_TYPE_CUSTOMER:
        return await build_customer_report_context(db, entity_id)
    return {}


async def _get_project_received(db: AsyncSession, project_id: int) -> float:
    from app.models.project import Milestone

    result = await db.execute(
        select(func.sum(Milestone.payment_amount)).where(
            Milestone.project_id == project_id,
            Milestone.payment_status == "received",
            Milestone.is_deleted == False,
        )
    )
    return float(result.scalar() or 0)


async def _get_project_hours(db: AsyncSession, project_id: int) -> float:
    from app.models.project import Project

    result = await db.execute(select(Project.actual_hours).where(Project.id == project_id))
    row = result.scalar_one_or_none()
    return float(row or 0)


async def _get_change_count(db: AsyncSession, project_id: int) -> int:
    try:
        from app.models.change_order import ChangeOrder
        from app.models.contract import Contract

        result = await db.execute(
            select(func.count(ChangeOrder.id))
            .join(Contract, Contract.id == ChangeOrder.contract_id)
            .where(
                Contract.project_id == project_id,
                ChangeOrder.is_deleted == False,
            )
        )
        return result.scalar() or 0
    except Exception:
        return 0


async def _get_acceptance_status(db: AsyncSession, project_id: int) -> str:
    try:
        from app.models.acceptance import Acceptance

        result = await db.execute(
            select(Acceptance).where(
                Acceptance.project_id == project_id,
                Acceptance.is_deleted == False,
            )
        )
        records = result.scalars().all()
        if not records:
            return "未验收"
        passed = all(r.status == "accepted" for r in records)
        return "已通过" if passed else "部分通过"
    except Exception:
        return "未知"


async def _get_direct_cost(db: AsyncSession, project_id: int) -> float:
    try:
        from app.models.finance import FinanceRecord

        result = await db.execute(
            select(func.sum(FinanceRecord.amount)).where(
                FinanceRecord.project_id == project_id,
                FinanceRecord.type == "expense",
                FinanceRecord.is_deleted == False,
            )
        )
        return float(result.scalar() or 0)
    except Exception:
        return 0


async def _get_outsource_cost(db: AsyncSession, project_id: int) -> float:
    try:
        from app.models.finance import FinanceRecord

        result = await db.execute(
            select(func.sum(FinanceRecord.amount)).where(
                FinanceRecord.project_id == project_id,
                FinanceRecord.type == "expense",
                FinanceRecord.category == "outsource",
                FinanceRecord.is_deleted == False,
            )
        )
        return float(result.scalar() or 0)
    except Exception:
        return 0


async def _get_payment_on_time_rate(db: AsyncSession, customer_id: int) -> float:
    from app.models.project import Milestone
    from app.models.project import Project

    result = await db.execute(
        select(Milestone).where(
            Milestone.project_id.in_(
                select(Project.id).where(Project.customer_id == customer_id, Project.is_deleted == False)
            ),
            Milestone.payment_status == "received",
            Milestone.is_deleted == False,
        )
    )
    milestones = result.scalars().all()
    if not milestones:
        return 100.0

    on_time = sum(1 for m in milestones if m.payment_due_date and m.payment_status == "received")
    return on_time / len(milestones) * 100
