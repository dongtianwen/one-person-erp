"""v1.10 帮助内容映射——纯 Python 字典，不入数据库，不建查询接口。

前端帮助内容在 frontend/src/constants/help.js，后端帮助内容在此文件。
"""

from __future__ import annotations

from app.core.constants import HELP_MAX_NEXT_STEPS

HELP_CONTENT: dict[str, dict] = {
    "TEMPLATE_NOT_FOUND": {
        "reason": "指定的模板不存在，请检查模板 ID 或选择其他模板。",
        "next_steps": [
            "前往「模板管理」页面",
            "确认模板是否存在或是否已被删除",
        ],
        "doc_anchor": "template-management",
    },
    "TEMPLATE_RENDER_FAILED": {
        "reason": "模板渲染失败，可能是模板语法错误或缺少必要变量。",
        "next_steps": [
            "前往「模板管理」页面检查模板内容",
            "确保所有必填变量已正确填充",
        ],
        "doc_anchor": "template-syntax",
    },
    "TEMPLATE_MISSING_REQUIRED_VARS": {
        "reason": "模板需要但未提供必填变量，无法生成内容。",
        "next_steps": [
            "检查当前数据是否包含所有必填字段",
            "如需临时使用，可手动补充变量值",
        ],
        "doc_anchor": "template-variables",
    },
    "CONTENT_FROZEN": {
        "reason": "内容已冻结，状态为「已接受」的报价单或「已激活」的合同不可重新生成或编辑内容。",
        "next_steps": [
            "如需修改内容，请先解除冻结状态（仅可编辑临时内容）",
            "如需重新生成，请先创建新报价/合同",
        ],
        "doc_anchor": "content-freeze",
    },
    "CONTENT_ALREADY_EXISTS": {
        "reason": "内容已存在，直接生成会覆盖现有内容。",
        "next_steps": [
            "点击「确认」覆盖现有内容",
            "或点击「取消」保持原有内容",
        ],
        "doc_anchor": "content-overwrite",
    },
    "QUOTE_NO_QUOTATION_ID": {
        "reason": "创建合同需要提供报价单 ID。",
        "next_steps": [
            "从报价单详情页点击「转合同」",
        ],
        "doc_anchor": "quote-contract",
    },
    "TEMPLATE_IS_DEFAULT": {
        "reason": "默认模板不可删除，如需修改可先设为非默认模板。",
        "next_steps": [
            "点击「设为默认」移除默认状态",
            "删除后再恢复为默认模板",
        ],
        "doc_anchor": "template-default",
    },
    "DRAFT_ALREADY_EXISTS": {
        "reason": "该项目已有报价草稿，请选择跳转到已有草稿或确认创建新草稿。",
        "next_steps": [
            "点击「跳转」查看已有草稿",
            "或点击「确认」创建新草稿（会覆盖现有草稿）",
        ],
        "doc_anchor": "draft-dedup",
    },
    "REQUIREMENT_FROZEN": {
        "reason": "该项目已关联报价单且报价状态为已接受，需求进入冻结状态，不允许直接修改。",
        "next_steps": [
            "前往项目详情页 → 变更单 Tab",
            "点击「新建变更单」，填写变更描述和额外费用",
            "等待变更单状态流转为 confirmed",
            "confirmed 后需求变更才正式生效",
        ],
        "doc_anchor": "change-order-flow",
    },
    "CHANGE_ORDER_INVALID_TRANSITION": {
        "reason": "变更单当前状态不允许执行此操作。confirmed/rejected/cancelled 为终态。",
        "next_steps": [
            "pending 状态可执行：确认、拒绝、撤回",
            "confirmed/rejected/cancelled 为终态，不可再操作",
            "如需重新提交，请新建一条变更单",
        ],
        "doc_anchor": "change-order-status",
    },
    "MILESTONE_NOT_COMPLETED": {
        "reason": "收款状态流转需要里程碑先标记为已完成。",
        "next_steps": [
            "前往项目详情页 → 里程碑列表",
            "找到对应里程碑，将状态更新为「已完成」",
            "完成后即可触发开票/收款流转",
        ],
        "doc_anchor": "milestone-payment",
    },
    "PROJECT_CLOSE_CONDITIONS_NOT_MET": {
        "reason": "项目关闭需要满足所有前置条件，当前有条件未满足。",
        "next_steps": [
            "点击「关闭条件检查」查看具体未满足项",
            "确保所有里程碑状态为已完成",
            "确保存在 acceptance_type=final 且 status=passed 的验收记录",
            "确保所有里程碑收款状态为已到账（或收款金额为0）",
            "确保至少有一条交付物记录",
        ],
        "doc_anchor": "project-close",
    },
    "PROJECT_ALREADY_CLOSED": {
        "reason": "项目已完成关闭，不可重复关闭，核心字段不可修改。",
        "next_steps": [
            "已关闭项目数据仅供查阅",
            "如需查看关闭条件快照，前往项目详情页查看 close_checklist",
        ],
        "doc_anchor": "project-close",
    },
    "INVOICE_AMOUNT_EXCEEDS_CONTRACT": {
        "reason": "同一合同下所有未作废发票的金额合计不得超过合同总金额。",
        "next_steps": [
            "前往合同详情页 → 发票 Tab 查看已开票金额进度条",
            "检查是否有重复开票",
            "如需开票金额超出合同，请先修改合同金额",
        ],
        "doc_anchor": "invoice-amount-limit",
    },
    "INVOICE_STATUS_INVALID_TRANSITION": {
        "reason": "发票状态只能按固定顺序流转：草稿→已开票→客户已收→已核销。",
        "next_steps": [
            "草稿可流转到：已开票、已作废",
            "已开票可流转到：客户已收、已作废",
            "客户已收可流转到：已核销",
            "已核销和已作废为终态，不可再操作",
        ],
        "doc_anchor": "invoice-status",
    },
    "INVOICE_CANNOT_DELETE": {
        "reason": "已核销（verified）和已作废（cancelled）的发票不允许删除，以保证财务记录完整性。",
        "next_steps": [
            "已核销发票如有问题请联系代理记账处理",
            "如需作废已开票发票，可将状态流转为「已作废」",
        ],
        "doc_anchor": "invoice-delete",
    },
    "QUOTE_ALREADY_CONVERTED": {
        "reason": "一张报价单只能转换为一份合同，该报价单已完成转换。",
        "next_steps": [
            "前往报价单详情页查看已关联的合同编号",
            "如需新合同，请重新创建报价单",
        ],
        "doc_anchor": "quote-convert",
    },
    "QUOTE_NOT_ACCEPTED": {
        "reason": "只有状态为「已接受」的报价单才能转换为合同。",
        "next_steps": [
            "先执行「接受」操作，将报价单状态变更为 accepted",
            "再执行「转换合同」",
        ],
        "doc_anchor": "quote-convert",
    },
    # v2.0 AI Agent 闭环
    "OLLAMA_UNAVAILABLE": {
        "reason": "Ollama 本地服务未启动或无法连接，请检查服务状态和配置。",
        "next_steps": [
            "确认 Ollama 服务已启动（默认端口 11434）",
            "检查 .env 中的 LLM_LOCAL_BASE_URL 配置是否正确",
            "如不需要 LLM 增强功能，可将 LLM_PROVIDER 设为 none",
        ],
        "doc_anchor": "agent-llm-config",
    },
    "API_PROVIDER_UNAVAILABLE": {
        "reason": "外部 LLM API 服务不可用，请检查 API 配置和网络连接。",
        "next_steps": [
            "检查 .env 中的 LLM_API_BASE 和 LLM_API_KEY 配置",
            "确认 API 服务正常运行且密钥有效",
            "如不需要 LLM 增强功能，可将 LLM_PROVIDER 设为 none",
        ],
        "doc_anchor": "agent-llm-config",
    },
    "LLM_PARSE_FAILED": {
        "reason": "LLM 返回的内容无法解析为预期的 JSON 格式。",
        "next_steps": [
            "Agent 已自动降级为规则引擎输出",
            "建议可正常使用，但缺少 LLM 语言增强",
            "可尝试更换 LLM 模型或 Provider",
        ],
        "doc_anchor": "agent-fallback",
    },
    "AGENT_ALREADY_RUNNING": {
        "reason": "同类型的 Agent 正在运行中，为避免数据不一致，不允许并发运行。",
        "next_steps": [
            "等待当前 Agent 运行完成（可查看 Agent 运行日志页）",
            "如确认当前运行已卡住，可手动取消后重试",
        ],
        "doc_anchor": "agent-concurrency",
    },
    "SUGGESTION_NOT_PENDING": {
        "reason": "该建议已被确认或拒绝，不可重复操作。",
        "next_steps": [
            "查看建议的当前状态（已确认/已拒绝）",
            "如需重新决策，请新建一条 Agent 运行",
        ],
        "doc_anchor": "suggestion-confirmation",
    },
    "ACTION_EXECUTION_FAILED": {
        "reason": "Agent 动作执行失败，可能原因包括表不存在、模板渲染失败等。",
        "next_steps": [
            "查看 Agent 运行日志中的错误详情",
            "确认所需的数据库表和功能模块已部署",
            "用户的确认决策不会被回滚，可手动补录动作",
        ],
        "doc_anchor": "action-failure",
    },
    # 以下错误码 detail 已足够说明，不需要 help 映射：
    # PAYMENT_STATUS_INVALID_TRANSITION — 通用提示已够用
    # QUOTE_STATUS_INVALID_TRANSITION — 通用提示已够用
    # NOT_FOUND — detail 已说明
    # VALIDATION_ERROR — detail 已说明
    # v2.1 自由问答
    "QA_REQUIRES_API_PROVIDER": {
        "reason": "经营问答功能需要接入外部大模型，当前 LLM_PROVIDER 不是 api。",
        "next_steps": [
            "前往「设置 → 智能体」页面配置外部 API",
            "填写 LLM_API_BASE、LLM_API_KEY、LLM_API_MODEL",
            "将 .env 中 LLM_PROVIDER 改为 api 后重启",
        ],
        "doc_anchor": "qa-api-setup",
    },
    "QA_CONTEXT_BUILD_FAILED": {
        "reason": "构建经营数据上下文失败，所有数据查询均出现异常。",
        "next_steps": [
            "检查 logs/ 目录中的详细错误信息",
            "确认数据库文件未损坏（可尝试运行备份恢复）",
        ],
        "doc_anchor": "qa-context",
    },
    # v2.1 深度报告
    "REPORT_TYPE_NOT_SUPPORTED": {
        "reason": "请求的报告类型不在支持列表中。",
        "next_steps": [
            "当前支持：report_project（项目复盘）/ report_customer（客户分析）",
            "确认请求参数拼写正确",
        ],
        "doc_anchor": "report-types",
    },
    "REPORT_ENTITY_NOT_FOUND": {
        "reason": "生成报告的目标实体（项目或客户）不存在。",
        "next_steps": [
            "确认 entity_id 正确",
            "确认该项目或客户未被删除",
        ],
        "doc_anchor": "report-entity",
    },
    "REPORT_LLM_FILL_FAILED": {
        "reason": "AI 分析段落填充失败，报告已生成但分析内容为占位文本，需手动补充。",
        "next_steps": [
            "检查当前 LLM Provider 是否可用",
            "可重新生成报告（新增版本，不覆盖旧版本）",
            "或手动编辑报告中的分析段落",
        ],
        "doc_anchor": "report-llm-fill",
    },
    # v2.1 交付质检
    "DELIVERY_QC_NO_PACKAGE": {
        "reason": "指定的交付包不存在，无法执行质检。",
        "next_steps": [
            "确认 package_id 正确",
            "前往交付包列表确认该包是否存在",
        ],
        "doc_anchor": "delivery-qc",
    },
}


def get_help(error_code: str) -> dict | None:
    """返回错误码对应帮助内容，不存在时返回 None。"""
    content = HELP_CONTENT.get(error_code)
    if not content:
        return None
    return {
        "reason": content["reason"],
        "next_steps": content["next_steps"][:HELP_MAX_NEXT_STEPS],
        **({"doc_anchor": content["doc_anchor"]} if "doc_anchor" in content else {}),
    }
