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
NOTES_SEPARATOR = "\n"   # notes 追加时的分隔符

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
    "rejected": [],   # 终态
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
HELP_MAX_NEXT_STEPS: int = 5          # 每条错误帮助最多显示步骤数
HELP_FIELD_TIP_MAX_LENGTH: int = 30   # 字段提示最大字符数（中文）
HELP_PAGE_TIP_MAX_ITEMS: int = 5      # 页面帮助抽屉最多条目数
