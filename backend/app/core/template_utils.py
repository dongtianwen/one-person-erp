"""v1.12 报价合同生成——模板渲染和内容生成工具函数。"""
import re
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from jinja2 import Environment, TemplateSyntaxError, TemplateError
from sqlalchemy.orm import Session

from app.core.constants import (
    CONTRACT_CONTENT_FROZEN_STATUS,
    CONTRACT_OPTIONAL_VARS,
    CONTRACT_REQUIRED_VARS,
    QUOTATION_CONTENT_FROZEN_STATUS,
    QUOTATION_OPTIONAL_VARS,
    QUOTATION_REQUIRED_VARS,
    TEMPLATE_TYPE_CONTRACT,
    TEMPLATE_TYPE_QUOTATION,
)
from app.core.error_codes import ERROR_CODES

logger = logging.getLogger(__name__)

# 创建 Jinja2 环境（全局单例）
_jinja_env = Environment()


def _format_date(value: Any) -> str:
    """将日期/时间值格式化为 YYYY-MM-DD 字符串。"""
    if value is None:
        return ""
    if isinstance(value, str):
        return value[:10]
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    return str(value)


def validate_template_syntax(template_content: str) -> tuple[bool, str]:
    """
    验证 Jinja2 模板语法是否正确。

    Args:
        template_content: 模板内容

    Returns:
        (is_valid, error_message) - 是否有效及错误信息
    """
    try:
        # 解析模板但不渲染
        _jinja_env.parse(template_content)
        return True, ""
    except TemplateSyntaxError as e:
        error_msg = f"模板语法错误: {str(e)}"
        logger.warning(error_msg)
        return False, error_msg
    except TemplateError as e:
        error_msg = f"模板错误: {str(e)}"
        logger.warning(error_msg)
        return False, error_msg


def get_default_template(db: Session, template_type: str) -> Optional[Dict[str, Any]]:
    """
    获取指定类型的默认模板。

    Args:
        db: 数据库会话
        template_type: 模板类型（quotation/contract）

    Returns:
        模板字典或 None
    """
    from app.models.template import Template

    template = db.query(Template).filter(
        Template.template_type == template_type,
        Template.is_default == 1
    ).first()

    if template:
        return {
            "id": template.id,
            "name": template.name,
            "template_type": template.template_type,
            "content": template.content,
            "description": template.description,
        }

    logger.error(f"未找到 {template_type} 的默认模板")
    return None


def build_quotation_context(
    quotation: Dict[str, Any],
    company_data: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    构建报价单模板上下文。

    变量名与 PRD 附录 A 完全对齐。
    必填变量从传入数据读，可选变量有值填入无值用空字符串。

    Args:
        quotation: 报价单数据
        company_data: 公司设置（乙方信息），可选

    Returns:
        上下文字典
    """
    company = company_data or {}

    # 必填变量
    context = {
        "quotation_no": quotation.get("quote_no", ""),
        "customer_name": quotation.get("customer_name", ""),
        "project_name": quotation.get("project_name", "") or quotation.get("title", ""),
        "requirement_summary": quotation.get("requirement_summary", ""),
        "estimate_days": quotation.get("estimate_days", 0),
        "total_amount": quotation.get("total_amount", 0),
        "valid_until": _format_date(quotation.get("valid_until")),
        "created_date": _format_date(quotation.get("created_at")),
    }

    # 可选变量：有值填入，无值用空字符串
    context.update({
        "daily_rate": quotation.get("daily_rate", "") or "",
        "direct_cost": quotation.get("direct_cost", "") or "",
        "risk_buffer_rate": quotation.get("risk_buffer_rate", "") or "",
        "tax_rate": quotation.get("tax_rate", "") or "",
        "tax_amount": quotation.get("tax_amount", "") or "",
        "discount_amount": quotation.get("discount_amount", "") or "",
        "subtotal_amount": quotation.get("subtotal_amount", "") or "",
        "notes": quotation.get("notes", ""),
        "company_name": company.get("company_name", ""),
        "payment_terms": quotation.get("payment_terms", ""),
    })

    return context


def build_contract_context(
    contract: Dict[str, Any],
    quotation: Optional[Dict[str, Any]] = None,
    project_data: Optional[Dict[str, Any]] = None,
    deliverables: Optional[list] = None,
    company_data: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    构建合同模板上下文。

    变量名与 PRD 附录 A 完全对齐。
    quotation_no 必须存在；可选变量优先从已有数据源自动填充：
    - project_scope: 项目 description
    - deliverables_desc: 从 deliverables 表聚合
    - payment_terms: 报价单 notes 中的付款条款
    - acceptance_criteria: 报价单 notes 中的验收内容

    Args:
        contract: 合同数据
        quotation: 关联的报价单数据（可选）
        project_data: 项目数据（可选），含 description
        deliverables: 交付物列表（可选），每项含 name/description/version_no/delivery_date
        company_data: 公司设置（乙方信息），可选

    Returns:
        上下文字典
    """
    company = company_data or {}

    # 必填变量
    context = {
        "contract_no": contract.get("contract_no", ""),
        "customer_name": contract.get("customer_name", ""),
        "project_name": contract.get("project_name", "") or contract.get("title", ""),
        "total_amount": contract.get("amount", 0),
        "sign_date": _format_date(contract.get("signed_date") or contract.get("sign_date")) or "待签署",
        "company_name": company.get("company_name", ""),
        "quotation_no": quotation.get("quote_no", "") if quotation else "",
    }

    # 可选变量：优先从已有数据自动填充
    notes = quotation.get("notes", "") or contract.get("notes", "") or ""

    context.update({
        "payment_terms": contract.get("payment_terms", "") or _auto_payment_terms(
            quotation, contract, notes
        ),
        "project_scope": contract.get("project_scope", "") or (
            project_data.get("description", "") if project_data else ""
        ),
        "deliverables_desc": contract.get("deliverables_desc", "") or (
            _format_deliverables(deliverables) if deliverables else ""
        ),
        "acceptance_criteria": contract.get("acceptance_criteria", "") or (
            _auto_acceptance_criteria(notes, quotation) if notes else ""
        ),
        "liability_clause": contract.get("liability_clause", ""),
        "notes": notes,
    })

    return context


def _auto_payment_terms(
    quotation: Optional[Dict[str, Any]],
    contract: Dict[str, Any],
    notes: str,
) -> str:
    """根据项目特征自动生成付款条款。"""
    total = float(quotation.get("total_amount", 0) or 0) if quotation else 0
    if total > 0:
        first = int(total * 0.3)
        second = int(total * 0.4)
        last = int(total - first - second)
        return (
            f"合同签订后7个工作日内支付30%预付款（¥{first:,}）；"
            f"项目中期交付后7个工作日内支付40%进度款（¥{second:,}）；"
            f"项目验收合格后7个工作日内支付剩余30%尾款（¥{last:,}）。"
        )
    return ""


def _format_deliverables(deliverables: list) -> str:
    """将交付物列表格式化为合同正文。"""
    if not deliverables:
        return ""
    lines = []
    for i, d in enumerate(deliverables, 1):
        name = d.get("name", "交付物")
        version = d.get("version_no", "")
        desc = d.get("description", "")
        date = _format_date(d.get("delivery_date"))
        parts = [f"  {i}. {name}"]
        if version:
            parts.append(f"（版本 {version}）")
        if desc:
            parts.append(f"：{desc}")
        if date:
            parts.append(f"，交付日期 {date}")
        lines.append("".join(parts))
    return "\n".join(lines)


def _auto_acceptance_criteria(
    notes: str,
    quotation: Optional[Dict[str, Any]],
) -> str:
    """根据项目特征自动生成验收标准。"""
    estimate_days = quotation.get("estimate_days", 0) if quotation else 0
    days = estimate_days if estimate_days > 0 else 90
    return (
        f"乙方完成全部交付物交付后，甲方应在 {days} 个工作日内完成验收。\n"
        f"验收标准以双方确认的需求文档（含功能、性能指标）为准。\n"
        f"验收不合格的，乙方应在甲方提出修改意见后 10 个工作日内完成整改并重新提交。"
    )


def render_template(
    template_content: str,
    context: Dict[str, Any],
    required_vars: Optional[list[str]] = None,
) -> tuple[str, Optional[str]]:
    """
    渲染 Jinja2 模板。

    先校验 required_vars（TEMPLATE_MISSING_REQUIRED_VARS），
    再渲染（TEMPLATE_RENDER_FAILED），两者互斥。

    Args:
        template_content: 模板内容
        context: 上下文字典
        required_vars: 必填变量列表（不传则跳过校验）

    Returns:
        (rendered_content, error_message) - 渲染内容和错误信息
    """
    # 验证模板语法
    is_valid, error_msg = validate_template_syntax(template_content)
    if not is_valid:
        return "", error_msg

    # 验证必填变量（先校验数据再渲染，不会同时触发）
    if required_vars:
        missing = [v for v in required_vars if v not in context or context[v] in (None, "")]
        if missing:
            error_msg = f"模板缺少必填变量: {', '.join(missing)}"
            logger.warning(error_msg)
            return "", error_msg

    try:
        # 渲染模板
        template = _jinja_env.from_string(template_content)
        rendered = template.render(**context)
        return rendered, ""
    except TemplateError as e:
        error_msg = f"模板渲染失败: {str(e)}"
        logger.error(error_msg)
        return "", error_msg


def is_content_frozen(status: str, template_type: str) -> bool:
    """
    检查内容是否处于冻结状态。

    Args:
        status: 当前状态
        template_type: 模板类型（quotation/contract）

    Returns:
        是否冻结
    """
    if template_type == TEMPLATE_TYPE_QUOTATION:
        return status == QUOTATION_CONTENT_FROZEN_STATUS
    if template_type == TEMPLATE_TYPE_CONTRACT:
        return status == CONTRACT_CONTENT_FROZEN_STATUS
    return False


def can_regenerate_content(
    status: str,
    template_type: str,
    has_content: bool,
    force: bool = False,
) -> tuple[bool, Optional[str]]:
    """
    检查是否可以重新生成内容。

    规则：
    - 冻结状态（accepted/active）不允许，即使 force=true
    - 已有内容且 force=false 返回 CONTENT_ALREADY_EXISTS
    - 已有内容且 force=true 允许覆盖

    Args:
        status: 当前状态
        template_type: 模板类型
        has_content: 是否已有内容
        force: 是否强制覆盖

    Returns:
        (can_regenerate, error_code) - 是否可重新生成及错误码
    """
    # 冻结状态：即使 force=true 也不允许
    if is_content_frozen(status, template_type):
        return False, ERROR_CODES["CONTENT_FROZEN"]

    # 已有内容且未传 force
    if has_content and not force:
        return False, ERROR_CODES["CONTENT_ALREADY_EXISTS"]

    return True, None


def update_content_generated_at(content_generated_at: Optional[datetime]) -> Optional[datetime]:
    """
    更新内容生成时间（当前时间）。

    Args:
        content_generated_at: 原内容生成时间

    Returns:
        新内容生成时间
    """
    return datetime.now()
