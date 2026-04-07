"""v1.3 全局常量定义——业务代码中禁止使用魔术数字。"""

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
CHANGE_ORDER_VALID_TRANSITIONS: dict[str, list[str]] = {
    "draft": ["sent", "confirmed", "completed"],
    "sent": ["confirmed", "completed"],
    "confirmed": ["in_progress", "completed"],
    "in_progress": ["completed"],
    "completed": [],  # 空列表 = 不允许任何流转
}

# ── 密码字段检测规则（仅检测字段名，不扫描字段值）────────────────
FORBIDDEN_FIELD_PATTERNS = ["password", "pwd", "secret", "passwd", "token"]