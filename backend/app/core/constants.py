"""v1.3 ~ v1.7 全局常量定义——业务代码中禁止使用魔术数字。"""

# ── 现金流预测 ──────────────────────────────────────────────
CASHFLOW_FORECAST_DAYS: int = 90  # 预测天数
CASHFLOW_WEEKS_PER_MONTH: float = 4.33  # 月均周数
CASHFLOW_HISTORY_MONTHS: int = 3  # 支出历史统计月数
WEEK_START_DAY: int = 0  # 0 = 周一（Python weekday()）

# 纳入现金流预测的合同状态（只有这两个，其他一律不算）
CASHFLOW_CONTRACT_STATUSES: list[str] = ["active", "executing"]

# ── 精度 ────────────────────────────────────────────────────
DECIMAL_PLACES: int = 2  # 金额精度（四舍五入位数）

# ── 外包协作 ────────────────────────────────────────────────
OUTSOURCE_CATEGORY: str = "outsourcing"

# ── 发票方向 ────────────────────────────────────────────────
INVOICE_DIRECTION_OUTPUT: str = "output"  # 开具（销项）
INVOICE_DIRECTION_INPUT: str = "input"  # 取得（进项）

# ── 发票类型 ────────────────────────────────────────────────
INVOICE_TYPE_GENERAL: str = "general"  # 普通发票
INVOICE_TYPE_SPECIAL: str = "special"  # 专用发票
INVOICE_TYPE_ELECTRONIC: str = "electronic"  # 电子发票

# ── 税务处理方式 ────────────────────────────────────────────
TAX_TREATMENT_INVOICED: str = "invoiced"  # 已取得发票
TAX_TREATMENT_WITHHOLDING: str = "withholding"  # 代扣个税
TAX_TREATMENT_NONE: str = "none"  # 无需处理

# ── v1.4 利润核算与导出 ──────────────────────────────────────
PROFIT_DECIMAL_PLACES: int = 2  # 利润率精度，保留 2 位小数
EXPORT_MAX_ROWS_PER_SHEET: int = 10000  # 单 Sheet 最大导出行数
EXPORT_DATE_FORMAT: str = "%Y-%m-%d"  # 导出文件中的日期格式

# ── v1.5 需求管理 ──────────────────────────────────────────
REQUIREMENT_VERSION_PREFIX = "v"
REQUIREMENT_SUMMARY_MAX_LENGTH = 10000
CHANGE_ORDER_PREFIX = "BG"
MAINTENANCE_REMINDER_DAYS_BEFORE = 30
NOTES_SEPARATOR = "\n"  # notes 追加时的分隔符

# ── 变更单状态流转白名单（精确定义，不得自行扩展） ──────
# v1.5 合同变更单状态流转
CHANGE_ORDER_VALID_TRANSITIONS: dict[str, list[str]] = {
    "draft": ["sent", "confirmed", "completed"],
    "sent": ["confirmed", "completed"],
    "confirmed": ["in_progress", "completed"],
    "in_progress": ["completed"],
    "completed": [],  # 空列表 = 不允许任何流转
}

# ── 密码字段检测规则（仅检测字段名，不扫描字段值）────────────────
FORBIDDEN_FIELD_PATTERNS = ["password", "pwd", "secret", "passwd", "token"]

# ── v1.6 报价模块 ───────────────────────────────────────────
QUOTE_NO_PREFIX: str = "BJ"  # 报价单编号前缀
QUOTE_VALID_DAYS_DEFAULT: int = 30  # 默认报价有效期天数
QUOTE_DECIMAL_PLACES: int = 2  # 金额精度
QUOTE_ESTIMATE_MAX_DAYS: int = 365  # 单个报价允许的最大预计工期
QUOTE_EXPIRE_WINDOW_DAYS: int = 0  # 过期判定窗口（0 = 严格按 valid_until < 今日）

# 报价状态流转白名单（expired 仅由事件驱动设置，不接受接口直接传入）
QUOTE_VALID_TRANSITIONS: dict[str, list[str]] = {
    "draft": ["sent", "accepted", "cancelled"],
    "sent": ["accepted", "rejected", "cancelled"],
    "accepted": [],
    "rejected": [],
    "expired": [],
    "cancelled": [],
}

# ── v1.7 项目执行控制 ────────────────────────────────────────
# 变更单状态白名单
CHANGE_ORDER_STATUS_WHITELIST: list[str] = ["pending", "confirmed", "rejected", "cancelled"]

# 变更单状态流转规则（精确定义，不得自行扩展）
# pending → confirmed / rejected / cancelled
# confirmed 除外的三个状态为终态，不可再流转
CHANGE_ORDER_VALID_TRANSITIONS_V17: dict[str, list[str]] = {
    "pending": ["confirmed", "rejected", "cancelled"],
    "confirmed": [],  # 终态
    "rejected": [],  # 终态
    "cancelled": [],  # 终态
}

# ── v1.8 财务对接模块 ───────────────────────────────────────────
# 发票管理
INVOICE_NO_PREFIX: str = "INV"  # 发票编号前缀
INVOICE_TAX_RATE_STANDARD: float = 0.13  # 标准增值税率
INVOICE_TAX_RATE_SMALL: float = 0.03  # 小规模纳税人税率

# 发票状态白名单
INVOICE_STATUS_WHITELIST: list[str] = ["draft", "issued", "received", "verified", "cancelled"]

# 发票状态流转规则（精确定义，不得自行扩展）
# draft → issued / received / verified / cancelled
# issued → received / verified / cancelled
# received → verified / cancelled
# verified / cancelled 为终态，不可再流转
INVOICE_VALID_TRANSITIONS: dict[str, list[str]] = {
    "draft": ["issued", "received", "verified", "cancelled"],
    "issued": ["received", "verified", "cancelled"],
    "received": ["verified", "cancelled"],
    "verified": [],  # 终态：财务人工确认核销
    "cancelled": [],  # 终态：作废
}

# 发票类型白名单
INVOICE_TYPE_WHITELIST: list[str] = ["standard", "ordinary", "electronic", "small_scale"]

# 对账状态白名单
RECONCILIATION_STATUS_WHITELIST: list[str] = ["pending", "matched", "verified"]

# 财务导出
EXPORT_DATE_FORMAT: str = "%Y-%m-%d"  # 导出文件中的日期格式
EXPORT_DECIMAL_PLACES: int = 2  # 导出金额精度
ACCOUNTING_PERIOD_FORMAT: str = "%Y-%m"  # 会计期间格式

# 导出格式（generic 为必达，其余预留常量但本版本不实现）
EXPORT_FORMAT_GENERIC: str = "generic"
EXPORT_FORMAT_KINGDEE: str = "kingdee"  # 预留，未实现
EXPORT_FORMAT_YOYO: str = "yoyo"  # 预留，未实现
EXPORT_FORMAT_CHANJET: str = "chanjet"  # 预留，未实现
EXPORT_FORMAT_SUPPORTED: list[str] = [EXPORT_FORMAT_GENERIC]  # 本版本只支持 generic

# 发票编号格式：INV-YYYYMMDD-序号（当日从 001 起）
# 税额计算：tax_amount = round(amount_excluding_tax * tax_rate, 2)
# 价税合计：total_amount = round(amount_excluding_tax + tax_amount, 2)
# 导出文件名格式：{export_type}_{target_format}_{batch_id}.xlsx
# 会计期间：交易日期所属自然月，格式 YYYY-MM

# ── v1.9 风险控制与成本视图 ─────────────────────────────────────
# 工时换算（唯一来源，禁止在业务代码中硬编码 8）
HOURS_PER_DAY: int = 8  # 1天=8小时，工时成本换算基准

# 风险控制
OVERDUE_PAYMENT_WARN_DAYS: int = 0  # payment_due_date < 今日即为逾期
CUSTOMER_OVERDUE_WARN_THRESHOLD: int = 1  # 逾期笔数 >= 1 → warning
CUSTOMER_OVERDUE_HIGH_THRESHOLD: int = 3  # 逾期笔数 >= 3 → high
CUSTOMER_OVERDUE_HIGH_RATIO: float = 0.30  # 逾期金额/合同总额 >= 30% → high

# 一致性校验
CONSISTENCY_CHECK_TOLERANCE: float = 0.01  # 金额差异容忍度，低于此值不报告

# 固定成本
FIXED_COST_PERIOD_WHITELIST: list[str] = ["monthly", "quarterly", "yearly", "onetime"]
FIXED_COST_CATEGORY_WHITELIST: list[str] = ["office", "cloud", "software", "equipment", "other"]

# 粗利润
GROSS_PROFIT_DECIMAL_PLACES: int = 2
GROSS_MARGIN_DECIMAL_PLACES: int = 4

# ── v1.10 帮助与引导 ────────────────────────────────────────────
HELP_CONTENT_VERSION: str = "1.10"
HELP_MAX_NEXT_STEPS: int = 5  # 每条错误帮助最多显示步骤数
HELP_FIELD_TIP_MAX_LENGTH: int = 30  # 字段提示最大字符数（中文）
HELP_PAGE_TIP_MAX_ITEMS: int = 5  # 页面帮助抽屉最多条目数

# ── v1.11 数据标注与模型开发交付台账 ──────────────────────────────
# 数据集版本
DATASET_VERSION_NO_PATTERN: str = r"^v\d+\.\d+$"
DATASET_VERSION_STATUS_WHITELIST: list[str] = ["draft", "ready", "in_use", "archived"]
DATASET_TYPE_WHITELIST: list[str] = ["image", "text", "audio", "video", "multimodal", "other"]
DATASET_VERSION_FROZEN_STATUSES: list[str] = ["ready", "in_use", "archived"]
DATASET_VERSION_FROZEN_FIELDS: list[str] = [
    "version_no",
    "dataset_id",
    "sample_count",
    "file_path",
    "data_source",
    "label_schema_version",
]

# 模型版本
MODEL_VERSION_NO_PATTERN: str = r"^v\d+\.\d+\.\d+$"
MODEL_VERSION_STATUS_WHITELIST: list[str] = ["training", "ready", "delivered", "deprecated"]
MODEL_VERSION_FROZEN_STATUSES: list[str] = ["ready", "delivered", "deprecated"]
MODEL_VERSION_FROZEN_FIELDS: list[str] = ["version_no", "experiment_id", "name", "file_path", "metrics"]

# 训练实验
EXPERIMENT_FROZEN_FIELDS: list[str] = ["project_id", "framework", "hyperparameters"]

# 标注任务
ANNOTATION_TASK_STATUS_WHITELIST: list[str] = [
    "pending",
    "in_progress",
    "quality_check",
    "rework",
    "completed",
    "cancelled",
]
ANNOTATION_TASK_VALID_TRANSITIONS: dict[str, list[str]] = {
    "pending": ["in_progress", "cancelled"],
    "in_progress": ["quality_check", "cancelled"],
    "quality_check": ["completed", "rework"],
    "rework": ["in_progress"],
    "completed": [],
    "cancelled": [],
}
ANNOTATION_SPEC_REQUIREMENT_TYPE: str = "annotation_spec"

# 交付包
DELIVERY_PACKAGE_STATUS_WHITELIST: list[str] = ["draft", "ready", "delivered", "accepted"]
DELIVERY_PACKAGE_VALID_TRANSITIONS: dict[str, list[str]] = {
    "draft": ["ready"],
    "ready": ["delivered"],
    "delivered": ["accepted"],
    "accepted": [],
}
ACCEPTANCE_TYPE_DATASET: str = "dataset"
ACCEPTANCE_TYPE_MODEL: str = "model"

# ── v1.12 报价合同生成与模板系统 ─────────────────────────────────────
# 模板类型
TEMPLATE_TYPE_QUOTATION: str = "quotation"
TEMPLATE_TYPE_CONTRACT: str = "contract"
TEMPLATE_TYPE_REPORT_PROJECT: str = "report_project"
TEMPLATE_TYPE_REPORT_CUSTOMER: str = "report_customer"
TEMPLATE_TYPE_DELIVERY: str = "delivery"
TEMPLATE_TYPE_RETROSPECTIVE: str = "retrospective"
TEMPLATE_TYPE_QUOTATION_CALC: str = "quotation_calc"
TEMPLATE_TYPE_WHITELIST: list[str] = [TEMPLATE_TYPE_QUOTATION, TEMPLATE_TYPE_CONTRACT, TEMPLATE_TYPE_REPORT_PROJECT, TEMPLATE_TYPE_REPORT_CUSTOMER, TEMPLATE_TYPE_DELIVERY, TEMPLATE_TYPE_RETROSPECTIVE, TEMPLATE_TYPE_QUOTATION_CALC]

# 报价单变量
QUOTATION_REQUIRED_VARS: list[str] = [
    "quotation_no",
    "customer_name",
    "project_name",
    "requirement_summary",
    "estimate_days",
    "total_amount",
    "valid_until",
    "created_date",
]

QUOTATION_OPTIONAL_VARS: list[str] = [
    "daily_rate",
    "direct_cost",
    "risk_buffer_rate",
    "tax_rate",
    "tax_amount",
    "discount_amount",
    "subtotal_amount",
    "notes",
    "company_name",
    "payment_terms",
]

# 合同变量
CONTRACT_REQUIRED_VARS: list[str] = [
    "contract_no",
    "customer_name",
    "project_name",
    "total_amount",
    "sign_date",
    "company_name",
    "quotation_no",
]

CONTRACT_OPTIONAL_VARS: list[str] = [
    "payment_terms",
    "project_scope",
    "deliverables_desc",
    "acceptance_criteria",
    "liability_clause",
    "notes",
]

# 内容冻结状态
QUOTATION_CONTENT_FROZEN_STATUS: str = "accepted"  # 报价单被接受时内容冻结
CONTRACT_CONTENT_FROZEN_STATUS: str = "active"  # 合同被激活时内容冻结

# 内容生成状态
CONTENT_STATUS_EMPTY: str = ""  # 无内容
CONTENT_STATUS_GENERATED: str = "generated"  # 已生成
CONTENT_STATUS_EDITED: str = "edited"  # 手工编辑
CONTENT_STATUS_FROZEN: str = "frozen"  # 已冻结（不可编辑/生成）

# ── v2.0 AI Agent 闭环 ─────────────────────────────────────────────
# LLM Provider
LLM_PROVIDER_NONE: str = "none"
LLM_PROVIDER_LOCAL: str = "local"
LLM_PROVIDER_API: str = "api"
LLM_PROVIDER_WHITELIST: list[str] = [LLM_PROVIDER_NONE, LLM_PROVIDER_LOCAL, LLM_PROVIDER_API]

# Agent 类型
AGENT_TYPE_BUSINESS_DECISION: str = "business_decision"
AGENT_TYPE_PROJECT_MANAGEMENT: str = "project_management"
AGENT_TYPE_DELIVERY_QC: str = "delivery_qc"
AGENT_TYPE_WHITELIST: list[str] = [AGENT_TYPE_BUSINESS_DECISION, AGENT_TYPE_PROJECT_MANAGEMENT, AGENT_TYPE_DELIVERY_QC]

# Agent 运行状态
AGENT_RUN_STATUS_WHITELIST: list[str] = ["running", "completed", "failed"]
AGENT_TRIGGER_TYPE_WHITELIST: list[str] = ["manual", "scheduled"]

# 建议类型
SUGGESTION_TYPE_OVERDUE_PAYMENT: str = "overdue_payment"
SUGGESTION_TYPE_PROFIT_ANOMALY: str = "profit_anomaly"
SUGGESTION_TYPE_MILESTONE_RISK: str = "milestone_risk"
SUGGESTION_TYPE_CASHFLOW_WARNING: str = "cashflow_warning"
SUGGESTION_TYPE_TASK_DELAY: str = "task_delay"
SUGGESTION_TYPE_CHANGE_IMPACT: str = "change_impact"
SUGGESTION_TYPE_DELIVERY_MISSING_MODEL: str = "delivery_missing_model"
SUGGESTION_TYPE_DELIVERY_MISSING_DATASET: str = "delivery_missing_dataset"
SUGGESTION_TYPE_DELIVERY_MISSING_ACCEPTANCE: str = "delivery_missing_acceptance"
SUGGESTION_TYPE_DELIVERY_VERSION_MISMATCH: str = "delivery_version_mismatch"
SUGGESTION_TYPE_DELIVERY_EMPTY_PACKAGE: str = "delivery_empty_package"
SUGGESTION_TYPE_DELIVERY_UNBOUND_PROJECT: str = "delivery_unbound_project"
SUGGESTION_TYPE_WHITELIST: list[str] = [
    SUGGESTION_TYPE_OVERDUE_PAYMENT,
    SUGGESTION_TYPE_PROFIT_ANOMALY,
    SUGGESTION_TYPE_MILESTONE_RISK,
    SUGGESTION_TYPE_CASHFLOW_WARNING,
    SUGGESTION_TYPE_TASK_DELAY,
    SUGGESTION_TYPE_CHANGE_IMPACT,
    SUGGESTION_TYPE_DELIVERY_MISSING_MODEL,
    SUGGESTION_TYPE_DELIVERY_MISSING_DATASET,
    SUGGESTION_TYPE_DELIVERY_MISSING_ACCEPTANCE,
    SUGGESTION_TYPE_DELIVERY_VERSION_MISMATCH,
    SUGGESTION_TYPE_DELIVERY_EMPTY_PACKAGE,
    SUGGESTION_TYPE_DELIVERY_UNBOUND_PROJECT,
]

# 建议状态
SUGGESTION_STATUS_WHITELIST: list[str] = ["pending", "confirmed", "rejected", "superseded"]

# 动作类型
ACTION_TYPE_CREATE_TODO: str = "create_todo"
ACTION_TYPE_CREATE_REMINDER: str = "create_reminder"
ACTION_TYPE_GENERATE_REPORT: str = "generate_report"
ACTION_TYPE_NONE: str = "none"
ACTION_TYPE_WHITELIST: list[str] = [
    ACTION_TYPE_CREATE_TODO,
    ACTION_TYPE_CREATE_REMINDER,
    ACTION_TYPE_GENERATE_REPORT,
    ACTION_TYPE_NONE,
]

# 动作状态
ACTION_STATUS_WHITELIST: list[str] = ["pending", "executed", "failed"]

# 决策类型
DECISION_TYPE_WHITELIST: list[str] = ["accepted", "rejected", "modified"]

# 优先级
PRIORITY_WHITELIST: list[str] = ["high", "medium", "low"]

# 规则引擎阈值
RULE_OVERDUE_PAYMENT_WARN_DAYS: int = 0  # payment_due_date < 今日即为逾期
RULE_CUSTOMER_OVERDUE_WARN_THRESHOLD: int = 1  # 逾期笔数 >= 1 → warning
RULE_CUSTOMER_OVERDUE_HIGH_THRESHOLD: int = 3  # 逾期笔数 >= 3 → high
RULE_CUSTOMER_OVERDUE_HIGH_RATIO: float = 0.30  # 逾期金额/合同总额 >= 30% → high
RULE_PROFIT_ANOMALY_DROP_THRESHOLD: float = 0.30  # 利润率下降 >= 30% → anomaly
RULE_MILESTONE_RISK_DAYS: int = 7  # 距到期 <= 7 天且未完成 → risk
RULE_TASK_DELAY_DAYS: int = 0  # due_date < 今日且未完成 → delay
RULE_CASHFLOW_URGENT_WEEKS: int = 4  # 未来 4 周现金流为负 → urgent
RULE_CASHFLOW_WARNING_WEEKS: int = 8  # 未来 8 周现金流为负 → warning

# 反馈权重规则
FEEDBACK_WEIGHT_RULES: dict[str, int] = {
    "decision_type": 3,
    "reason_code": 2,
    "corrected_fields": 2,
    "user_priority_override": 2,
    "free_text_reason": 1,
}

# LLM 上下文最大记录数
FEEDBACK_CONTEXT_MAX_RECORDS: int = 30
LLM_RETRY_MAX_ATTEMPTS: int = 1
LLM_TIMEOUT_SECONDS: int = 180

# ── v2.1 模板类型（扩展 v1.12 白名单）────────────────────────────
# (TEMPLATE_TYPE_REPORT_PROJECT / TEMPLATE_TYPE_REPORT_CUSTOMER 已在 v1.12 区块定义)

# ── v2.1 报告相关 ──────────────────────────────────────────────
REPORT_TYPE_PROJECT: str = "report_project"
REPORT_TYPE_CUSTOMER: str = "report_customer"
REPORT_TYPE_WHITELIST: list[str] = [REPORT_TYPE_PROJECT, REPORT_TYPE_CUSTOMER]

REPORT_STATUS_GENERATING: str = "generating"
REPORT_STATUS_COMPLETED: str = "completed"
REPORT_STATUS_FAILED: str = "failed"

PROJECT_REPORT_LLM_VARS: list[str] = [
    "analysis_summary",
    "risk_retrospective",
    "improvement_suggestions",
]
CUSTOMER_REPORT_LLM_VARS: list[str] = [
    "value_assessment",
    "relationship_summary",
    "next_action_suggestions",
]

REPORT_LLM_FALLBACK_TEXT: str = "（AI 分析不可用，请手动补充）"

# ── v2.1 Agent 类型（扩展 v2.0 白名单）────────────────────────────
# (AGENT_TYPE_DELIVERY_QC 已在 v2.0 区块定义)

# ── v2.1 质检建议类型（新增）──────────────────────────────────────
# (SUGGESTION_TYPE_DELIVERY_* 已在 v2.0 建议类型区块定义)

# ── v2.1 自由问答 ──────────────────────────────────────────────
QA_CONTEXT_MONTHS: int = 3
QA_CONTEXT_MAX_PROJECTS: int = 10
QA_CONTEXT_MAX_TOKENS_ESTIMATE: int = 2000
QA_MAX_HISTORY_TURNS: int = 10

# ── v2.2 快照底座 + 仪表盘聚合层 ─────────────────────────────────────
# 快照实体类型
SNAPSHOT_ENTITY_TYPE_REPORT: str = "report"
SNAPSHOT_ENTITY_TYPE_MINUTES: str = "minutes"
SNAPSHOT_ENTITY_TYPE_TEMPLATE: str = "template"
SNAPSHOT_ENTITY_TYPE_WHITELIST: list[str] = [
    SNAPSHOT_ENTITY_TYPE_REPORT,
    SNAPSHOT_ENTITY_TYPE_MINUTES,
    SNAPSHOT_ENTITY_TYPE_TEMPLATE,
]

# Warning Code（snapshot / summary 失败路径）
WARNING_SNAPSHOT_WRITE_FAILED: str = "SNAPSHOT_WRITE_FAILED"
WARNING_SUMMARY_REFRESH_FAILED: str = "SUMMARY_REFRESH_FAILED"

# Dashboard Summary metric_key 常量
METRIC_CLIENT_COUNT: str = "client_count"
METRIC_CLIENT_RISK_HIGH_COUNT: str = "client_risk_high_count"
METRIC_PROJECT_ACTIVE_COUNT: str = "project_active_count"
METRIC_PROJECT_AT_RISK_COUNT: str = "project_at_risk_count"
METRIC_CONTRACT_ACTIVE_COUNT: str = "contract_active_count"
METRIC_CONTRACT_TOTAL_AMOUNT: str = "contract_total_amount"
METRIC_FINANCE_RECEIVABLE_TOTAL: str = "finance_receivable_total"
METRIC_FINANCE_OVERDUE_TOTAL: str = "finance_overdue_total"
METRIC_FINANCE_OVERDUE_COUNT: str = "finance_overdue_count"
METRIC_DELIVERY_IN_PROGRESS_COUNT: str = "delivery_in_progress_count"
METRIC_DELIVERY_COMPLETED_THIS_MONTH: str = "delivery_completed_this_month"
METRIC_AGENT_PENDING_COUNT: str = "agent_pending_count"
METRIC_AGENT_HIGH_PRIORITY_COUNT: str = "agent_high_priority_count"
DASHBOARD_METRIC_KEY_WHITELIST: list[str] = [
    METRIC_CLIENT_COUNT,
    METRIC_CLIENT_RISK_HIGH_COUNT,
    METRIC_PROJECT_ACTIVE_COUNT,
    METRIC_PROJECT_AT_RISK_COUNT,
    METRIC_CONTRACT_ACTIVE_COUNT,
    METRIC_CONTRACT_TOTAL_AMOUNT,
    METRIC_FINANCE_RECEIVABLE_TOTAL,
    METRIC_FINANCE_OVERDUE_TOTAL,
    METRIC_FINANCE_OVERDUE_COUNT,
    METRIC_DELIVERY_IN_PROGRESS_COUNT,
    METRIC_DELIVERY_COMPLETED_THIS_MONTH,
    METRIC_AGENT_PENDING_COUNT,
    METRIC_AGENT_HIGH_PRIORITY_COUNT,
]

# Summary 刷新触发事件
SUMMARY_TRIGGER_CONTRACT_CONFIRMED: str = "contract_confirmed"
SUMMARY_TRIGGER_PAYMENT_RECORDED: str = "payment_recorded"
SUMMARY_TRIGGER_INVOICE_RECORDED: str = "invoice_recorded"
SUMMARY_TRIGGER_DELIVERY_COMPLETED: str = "delivery_completed"
SUMMARY_TRIGGER_MILESTONE_CHANGED: str = "milestone_changed"
SUMMARY_TRIGGER_WHITELIST: list[str] = [
    SUMMARY_TRIGGER_CONTRACT_CONFIRMED,
    SUMMARY_TRIGGER_PAYMENT_RECORDED,
    SUMMARY_TRIGGER_INVOICE_RECORDED,
    SUMMARY_TRIGGER_DELIVERY_COMPLETED,
    SUMMARY_TRIGGER_MILESTONE_CHANGED,
]

# 触发事件 → 受影响的 metric_key 映射
SUMMARY_TRIGGER_METRIC_MAP: dict[str, list[str]] = {
    SUMMARY_TRIGGER_CONTRACT_CONFIRMED: [
        METRIC_CONTRACT_ACTIVE_COUNT,
        METRIC_CONTRACT_TOTAL_AMOUNT,
        METRIC_FINANCE_RECEIVABLE_TOTAL,
    ],
    SUMMARY_TRIGGER_PAYMENT_RECORDED: [
        METRIC_FINANCE_RECEIVABLE_TOTAL,
        METRIC_FINANCE_OVERDUE_TOTAL,
        METRIC_FINANCE_OVERDUE_COUNT,
    ],
    SUMMARY_TRIGGER_INVOICE_RECORDED: [
        METRIC_FINANCE_RECEIVABLE_TOTAL,
    ],
    SUMMARY_TRIGGER_DELIVERY_COMPLETED: [
        METRIC_DELIVERY_IN_PROGRESS_COUNT,
        METRIC_DELIVERY_COMPLETED_THIS_MONTH,
    ],
    SUMMARY_TRIGGER_MILESTONE_CHANGED: [
        METRIC_PROJECT_AT_RISK_COUNT,
        METRIC_FINANCE_OVERDUE_TOTAL,
        METRIC_FINANCE_OVERDUE_COUNT,
    ],
}

# 工具入口台账状态
TOOL_STATUS_PENDING: str = "pending"
TOOL_STATUS_IN_PROGRESS: str = "in_progress"
TOOL_STATUS_DONE: str = "done"
TOOL_STATUS_BACKFILLED: str = "backfilled"
TOOL_ENTRY_STATUS_WHITELIST: list[str] = [
    TOOL_STATUS_PENDING,
    TOOL_STATUS_IN_PROGRESS,
    TOOL_STATUS_DONE,
    TOOL_STATUS_BACKFILLED,
]
TOOL_ENTRY_VALID_TRANSITIONS: dict[str, list[str]] = {
    TOOL_STATUS_PENDING: [TOOL_STATUS_IN_PROGRESS, TOOL_STATUS_DONE],
    TOOL_STATUS_IN_PROGRESS: [TOOL_STATUS_DONE],
    TOOL_STATUS_DONE: [TOOL_STATUS_BACKFILLED],
    TOOL_STATUS_BACKFILLED: [],
}

# 客户线索台账
LEAD_SOURCE_WHITELIST: list[str] = ["referral", "website", "event", "cold_outreach", "other"]
LEAD_STATUS_INITIAL: str = "initial_contact"
LEAD_STATUS_INTENT_CONFIRMED: str = "intent_confirmed"
LEAD_STATUS_CONVERTED: str = "converted"
LEAD_STATUS_INVALID: str = "invalid"
LEAD_STATUS_WHITELIST: list[str] = [
    LEAD_STATUS_INITIAL,
    LEAD_STATUS_INTENT_CONFIRMED,
    LEAD_STATUS_CONVERTED,
    LEAD_STATUS_INVALID,
]
LEAD_VALID_TRANSITIONS: dict[str, list[str]] = {
    LEAD_STATUS_INITIAL: [LEAD_STATUS_INTENT_CONFIRMED, LEAD_STATUS_INVALID],
    LEAD_STATUS_INTENT_CONFIRMED: [LEAD_STATUS_CONVERTED, LEAD_STATUS_INVALID],
    LEAD_STATUS_CONVERTED: [],
    LEAD_STATUS_INVALID: [],
}
