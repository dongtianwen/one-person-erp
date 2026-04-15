# 数标云管 v2.0 — Claude Code 执行指令 R3（AI 智能体闭环层）

## 项目目标

在 v1.0 ~ v1.12 已有经营底座上，新增 AI 智能体闭环层。
系统升级为：**规则引擎默认驱动 + 三档 LLM Provider 可选语言增强 + 人工确认闭环**。

本版本不做：自由问答、深度报告、增强分析、多人协作、云同步、自动外发、知识图谱、交付质检智能体。

**R3 相较 R2 的修正点（两处）**：
1. 簇 D `enhance_suggestions` 补充 JSON 解析增强策略（few-shot + 后处理 + 单次重试）
2. 簇 D `build_llm_context` 补充反馈聚合定义（同组合去重，取最近一条）

---

## 零、关键语义边界定义（实施前必读，禁止跳过）

### 0.1 智能体分层定义

```
规则引擎层（Rule Engine）：
  - 系统默认运行态，三档 Provider 均依赖此层
  - 读取真实经营数据，按常量阈值判断异常
  - 输出结构化建议列表（JSON）
  - 决策逻辑全部在此层，LLM 不参与决策

LLM Provider 层（三档可选）：
  - none：纯规则输出，无任何 LLM 调用
  - local：Ollama + gemma4:e2b，本地语言增强
  - api：外部 API（url / key 由 .env 配置），语言增强
  - v2.0 三档均只做语言增强，不做自由问答或深度报告
  - 任意 Provider 不可用时，系统降级为规则文本输出，不报错、不阻断

人工确认层（Human Confirmation）：
  - 所有建议必须经用户确认才能执行动作
  - Agent 可自动执行：创建待办、创建提醒
  - 必须人工确认：修改合同、确认回款、关闭项目、项目范围变更
```

### 0.2 参赛口径（执行指令注释，非代码）

```
系统定位：规则引擎保证离线可用，AI 模型负责语言增强与解释，
          人工确认保证经营安全，形成可审计的经营闭环。

手动触发是有意的安全控制策略，不是系统缺少感知能力。
一人公司的经营安全边界要求：系统自动感知异常，关键路径由人工触发/确认。
这比"全自动 Agent"更符合一人公司真实经营场景。
```

### 0.3 闭环定义（可验证，非口号）

```
感知 = 规则引擎读取 DB 数据
分析 = 规则引擎按阈值计算 + LLM 语言化（由 Provider 决定是否调用）
决策 = 生成 agent_suggestions 记录
执行 = 用户确认后，系统执行 agent_actions
反馈 = 用户决策写入 human_confirmations（字段级）
优化 = 下次运行时，FEEDBACK_WEIGHT_RULES 将历史反馈结构化注入 LLM 上下文
       （非 prompt 拼接：规则字典定义了哪些反馈影响建议摘要，有测试验证）
```

### 0.4 MVP 范围（精确）

```
✅ 经营决策智能体（全功能）
✅ 三档 LLM Provider 架构（none / local / api）
✅ 建议确认与动作执行机制
✅ 结构化反馈注入（FEEDBACK_WEIGHT_RULES）
✅ 智能体运行日志
✅ 规则引擎兜底
✅ 项目管理智能体（仅限：延期识别 + 变更影响分析）
❌ 自由问答（v2.1）
❌ 深度报告（v2.1）
❌ 交付/质检智能体（v2.1）
❌ 自动触发（所有 Agent 均为用户手动触发）
```

### 0.5 错误码边界

```python
# OLLAMA_UNAVAILABLE：local Provider 不可访问——降级，不阻断
# API_PROVIDER_UNAVAILABLE：api Provider 不可访问——降级，不阻断
# LLM_PARSE_FAILED：LLM 输出解析失败（含重试后仍失败）——降级，不阻断
# AGENT_ALREADY_RUNNING：同类型 Agent 正在运行——409
# SUGGESTION_NOT_PENDING：建议不在 pending 状态——拒绝确认
# ACTION_EXECUTION_FAILED：动作执行失败——记录，不回滚确认状态
```

### 0.6 LLM 调用约束（三档通用）

```python
# 超时：30 秒（硬超时，超时即降级，不重试）
# JSON 解析失败：先执行后处理提取，再单次重试（简化 prompt），仍失败则降级
# 重试次数：最多 1 次，不做多次重试
# Prompt 约束：要求模型只输出 JSON，不输出任何前缀/后缀/markdown
# 知识依赖：LLM 不依赖自身知识判断经营数据，所有数据由 context 注入
# v2.0 范围：三档均只做语言增强，api Provider 不开放增强分析端点
```

---

## 一、前置检查

```bash
pytest tests/ -v --tb=short  # 要求 0 FAILED

# 确认以下表存在：projects / contracts / finance_records / milestones /
#   tasks / quotations / fixed_costs
# 记录现金流预测表、待办表、提醒表的实际表名到 PROGRESS.md

# 检查 .env 文件，若无以下字段则追加（默认值如下）：
# LLM_PROVIDER=none
# LLM_LOCAL_MODEL=gemma4:e2b
# LLM_LOCAL_BASE_URL=http://localhost:11434
# LLM_API_BASE=
# LLM_API_KEY=
# LLM_API_MODEL=

# local Provider 检查（仅当 LLM_PROVIDER=local 时执行）：
python -c "import ollama; print('ollama ok')" || pip install ollama --break-system-packages
curl http://localhost:11434/api/tags || echo "Ollama 未启动，已记录，继续执行"
```

PROGRESS.md 初始化：
```
## v2.0 执行进度

| 簇 | 描述 | 状态 |
|----|------|------|
| A  | 数据库迁移（4 张 Agent 表） | ⏳ |
| B  | 全局常量与错误码 | ⏳ |
| C  | 规则引擎 | ⏳ |
| D  | LLM Provider 抽象层（三档） | ⏳ |
| E  | Agent 运行 API | ⏳ |
| F  | 建议确认与动作执行 API | ⏳ |
| G  | 前端联调 | ⏳ |
| H  | 全局重构与验证 | ⏳ |

## 实际表名记录（前置检查后填写）
- 现金流预测表：[待填写]
- 待办表：[待填写，若不存在则在簇 A 新增]
- 提醒表：[待填写，若不存在则在簇 A 新增]
```

---

## 二、全局常量（追加到 `backend/core/constants.py`）

```python
# ── LLM Provider ──────────────────────────────────────────
LLM_PROVIDER_LOCAL = "local"
LLM_PROVIDER_API = "api"
LLM_PROVIDER_NONE = "none"
LLM_PROVIDER_WHITELIST = [LLM_PROVIDER_LOCAL, LLM_PROVIDER_API, LLM_PROVIDER_NONE]

OLLAMA_TIMEOUT_SECONDS = 30
OLLAMA_HEALTH_CHECK_TIMEOUT = 3
API_PROVIDER_TIMEOUT_SECONDS = 30
API_PROVIDER_HEALTH_CHECK_TIMEOUT = 5

# LLM JSON 解析策略
LLM_PARSE_MAX_RETRIES = 1           # 解析失败后最多重试 1 次（简化 prompt 重试）
LLM_PARSE_EXTRACT_BRACKETS = True   # 解析前先尝试提取 [...] 之间的内容

# ── Agent 类型 ──────────────────────────────────────────
AGENT_TYPE_BUSINESS_DECISION = "business_decision"
AGENT_TYPE_PROJECT_MANAGEMENT = "project_management"
AGENT_TYPE_WHITELIST = [AGENT_TYPE_BUSINESS_DECISION, AGENT_TYPE_PROJECT_MANAGEMENT]

# ── Agent 运行状态 ────────────────────────────────────────
AGENT_STATUS_RUNNING = "running"
AGENT_STATUS_COMPLETED = "completed"
AGENT_STATUS_FAILED = "failed"

# ── 建议类型 ─────────────────────────────────────────────
SUGGESTION_TYPE_OVERDUE_PAYMENT = "overdue_payment"
SUGGESTION_TYPE_PROFIT_ANOMALY = "profit_anomaly"
SUGGESTION_TYPE_MILESTONE_RISK = "milestone_risk"
SUGGESTION_TYPE_CASHFLOW_WARNING = "cashflow_warning"
SUGGESTION_TYPE_TASK_DELAY = "task_delay"
SUGGESTION_TYPE_CHANGE_IMPACT = "change_impact"

# ── 建议优先级 ────────────────────────────────────────────
SUGGESTION_PRIORITY_HIGH = "high"
SUGGESTION_PRIORITY_MEDIUM = "medium"
SUGGESTION_PRIORITY_LOW = "low"
SUGGESTION_PRIORITY_NUDGE_UP = +1
SUGGESTION_PRIORITY_NUDGE_DOWN = -1

# ── 建议状态 ─────────────────────────────────────────────
SUGGESTION_STATUS_PENDING = "pending"
SUGGESTION_STATUS_CONFIRMED = "confirmed"
SUGGESTION_STATUS_REJECTED = "rejected"
SUGGESTION_STATUS_EXECUTED = "executed"

# ── 动作类型 ─────────────────────────────────────────────
ACTION_TYPE_CREATE_TODO = "create_todo"
ACTION_TYPE_CREATE_REMINDER = "create_reminder"
ACTION_TYPE_GENERATE_REPORT = "generate_report"

ACTION_STATUS_PENDING = "pending"
ACTION_STATUS_EXECUTED = "executed"
ACTION_STATUS_FAILED = "failed"

# ── 人工确认 ─────────────────────────────────────────────
DECISION_TYPE_ACCEPTED = "accepted"
DECISION_TYPE_REJECTED = "rejected"
DECISION_TYPE_MODIFIED = "modified"

REASON_CODE_NOT_APPLICABLE = "not_applicable"
REASON_CODE_ALREADY_HANDLED = "already_handled"
REASON_CODE_DISAGREE_ANALYSIS = "disagree_with_analysis"
REASON_CODE_OTHER = "other"

# ── 规则引擎阈值 ──────────────────────────────────────────
OVERDUE_PAYMENT_WARNING_DAYS = 30
OVERDUE_PAYMENT_HIGH_RISK_DAYS = 60
PROFIT_ANOMALY_THRESHOLD_RATE = 0.15
CASHFLOW_WARNING_DAYS = 30
MILESTONE_RISK_DAYS = 7
TASK_DELAY_WARNING_DAYS = 3

# ── 反馈权重规则 ──────────────────────────────────────────
# key: (decision_type, suggestion_type)
# value: priority_nudge（+1上调/-1下调）+ note（注入 LLM context 的摘要文字）
# 语义：priority_nudge 不修改规则引擎的 priority 字段，
#       只影响注入 LLM 上下文时的描述方式（告知模型用户历史偏好）
# 聚合规则：同一 key 在历史记录中出现多次时，只注入最近一条，不重复注入
FEEDBACK_WEIGHT_RULES = {
    (DECISION_TYPE_ACCEPTED, SUGGESTION_TYPE_OVERDUE_PAYMENT): {
        "priority_nudge": SUGGESTION_PRIORITY_NUDGE_UP,
        "note": "用户通常重视逾期回款提醒",
    },
    (DECISION_TYPE_REJECTED, SUGGESTION_TYPE_OVERDUE_PAYMENT): {
        "priority_nudge": SUGGESTION_PRIORITY_NUDGE_DOWN,
        "note": "用户上次忽略了逾期回款提醒，可能已自行处理",
    },
    (DECISION_TYPE_ACCEPTED, SUGGESTION_TYPE_CASHFLOW_WARNING): {
        "priority_nudge": SUGGESTION_PRIORITY_NUDGE_UP,
        "note": "用户通常重视现金流预警",
    },
    (DECISION_TYPE_REJECTED, SUGGESTION_TYPE_CASHFLOW_WARNING): {
        "priority_nudge": SUGGESTION_PRIORITY_NUDGE_DOWN,
        "note": "用户上次忽略了现金流预警",
    },
    (DECISION_TYPE_ACCEPTED, SUGGESTION_TYPE_PROFIT_ANOMALY): {
        "priority_nudge": SUGGESTION_PRIORITY_NUDGE_UP,
        "note": "用户通常关注利润异常",
    },
    (DECISION_TYPE_REJECTED, SUGGESTION_TYPE_PROFIT_ANOMALY): {
        "priority_nudge": SUGGESTION_PRIORITY_NUDGE_DOWN,
        "note": "用户上次忽略了利润异常提示",
    },
    (DECISION_TYPE_ACCEPTED, SUGGESTION_TYPE_MILESTONE_RISK): {
        "priority_nudge": SUGGESTION_PRIORITY_NUDGE_UP,
        "note": "用户通常重视里程碑风险",
    },
    (DECISION_TYPE_REJECTED, SUGGESTION_TYPE_MILESTONE_RISK): {
        "priority_nudge": SUGGESTION_PRIORITY_NUDGE_DOWN,
        "note": "用户上次忽略了里程碑风险提示",
    },
    (DECISION_TYPE_ACCEPTED, SUGGESTION_TYPE_TASK_DELAY): {
        "priority_nudge": SUGGESTION_PRIORITY_NUDGE_UP,
        "note": "用户通常关注任务延期",
    },
    (DECISION_TYPE_REJECTED, SUGGESTION_TYPE_TASK_DELAY): {
        "priority_nudge": SUGGESTION_PRIORITY_NUDGE_DOWN,
        "note": "用户上次忽略了任务延期提示",
    },
    # change_impact 不参与权重调整（人工处理类，拒绝不代表偏好）
}

FEEDBACK_CONTEXT_MAX_RECORDS = 30   # 查询历史反馈的最大条数（聚合前）
```

追加到 `backend/core/error_codes.py`：
```python
ERROR_OLLAMA_UNAVAILABLE = "OLLAMA_UNAVAILABLE"
ERROR_API_PROVIDER_UNAVAILABLE = "API_PROVIDER_UNAVAILABLE"
ERROR_LLM_PARSE_FAILED = "LLM_PARSE_FAILED"
ERROR_AGENT_ALREADY_RUNNING = "AGENT_ALREADY_RUNNING"
ERROR_SUGGESTION_NOT_PENDING = "SUGGESTION_NOT_PENDING"
ERROR_ACTION_EXECUTION_FAILED = "ACTION_EXECUTION_FAILED"
```

---

## 三、执行清单

---

### 簇 A：数据库迁移

#### A.1 新增 4 张 Agent 核心表

```sql
CREATE TABLE IF NOT EXISTS agent_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_type VARCHAR(50) NOT NULL,
    trigger_type VARCHAR(20) NOT NULL DEFAULT 'manual',
    status VARCHAR(20) NOT NULL DEFAULT 'running',
    llm_provider VARCHAR(20) NOT NULL DEFAULT 'none',
    rule_output TEXT NULL,
    llm_enhanced INTEGER NOT NULL DEFAULT 0,
    llm_model VARCHAR(100) NULL,
    context_snapshot TEXT NULL,
    error_message TEXT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL
);
CREATE INDEX IF NOT EXISTS idx_agent_runs_type_status
    ON agent_runs(agent_type, status);
CREATE INDEX IF NOT EXISTS idx_agent_runs_created_at
    ON agent_runs(created_at DESC);

CREATE TABLE IF NOT EXISTS agent_suggestions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_run_id INTEGER NOT NULL REFERENCES agent_runs(id),
    suggestion_type VARCHAR(50) NOT NULL,
    priority VARCHAR(10) NOT NULL,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    suggested_action VARCHAR(50) NULL,
    action_params TEXT NULL,
    source VARCHAR(20) NOT NULL DEFAULT 'rule',  -- rule/local/api
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_agent_suggestions_run
    ON agent_suggestions(agent_run_id);
CREATE INDEX IF NOT EXISTS idx_agent_suggestions_status
    ON agent_suggestions(status);

CREATE TABLE IF NOT EXISTS agent_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    suggestion_id INTEGER NOT NULL REFERENCES agent_suggestions(id),
    action_type VARCHAR(50) NOT NULL,
    action_params TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    executed_at TIMESTAMP NULL,
    result TEXT NULL,
    error_message TEXT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_agent_actions_suggestion
    ON agent_actions(suggestion_id);

CREATE TABLE IF NOT EXISTS human_confirmations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_run_id INTEGER NOT NULL REFERENCES agent_runs(id),
    suggestion_id INTEGER NOT NULL REFERENCES agent_suggestions(id),
    decision_type VARCHAR(20) NOT NULL,
    reason_code VARCHAR(50) NULL,
    free_text_reason TEXT NULL,
    corrected_fields TEXT NULL,
    user_priority_override VARCHAR(10) NULL,
    inject_to_next_run INTEGER NOT NULL DEFAULT 1,
    next_review_at DATE NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_human_confirmations_suggestion
    ON human_confirmations(suggestion_id);
CREATE INDEX IF NOT EXISTS idx_human_confirmations_inject
    ON human_confirmations(inject_to_next_run, created_at);
```

#### A.2 待办/提醒表（按 PROGRESS.md 实际表名适配；不存在则创建）

```sql
CREATE TABLE IF NOT EXISTS todos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(200) NOT NULL,
    description TEXT NULL,
    due_date DATE NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    source VARCHAR(50) NULL,
    source_id INTEGER NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

#### A.3 测试文件 `tests/test_migration_v200.py`

```python
# test_agent_runs_table_exists → NFR-2001
# test_agent_suggestions_table_exists → NFR-2001
# test_agent_actions_table_exists → NFR-2001
# test_human_confirmations_table_exists → NFR-2001
# test_agent_runs_llm_provider_column_exists → NFR-2001
# test_agent_suggestions_source_column_exists → NFR-2001
# test_agent_runs_index_type_status → NFR-2001
# test_agent_suggestions_index_status → NFR-2001
# test_human_confirmations_index_inject → NFR-2001
# test_todos_table_exists_or_equivalent → NFR-2001
# test_existing_tables_row_counts_unchanged → NFR-2001
# test_existing_tables_fields_unchanged → NFR-2001
```

运行全量测试，0 FAILED。更新 PROGRESS.md，继续簇 B。

---

### 簇 B：全局常量验证

```python
# tests/test_constants_v200.py
# test_llm_provider_whitelist_complete → NFR-2002
# test_agent_type_whitelist_complete → NFR-2002
# test_feedback_weight_rules_keys_valid_decision_types → NFR-2002
# test_feedback_weight_rules_keys_valid_suggestion_types → NFR-2002
# test_feedback_weight_rules_values_have_required_fields → NFR-2002
# test_feedback_weight_rules_nudge_values_are_plus_or_minus_one → NFR-2002
# test_llm_parse_max_retries_is_one → NFR-2002
# test_suggestion_type_constants_defined → NFR-2002
# test_rule_threshold_constants_defined → NFR-2002
# test_no_magic_numbers_in_rule_engine_module → NFR-2002
```

运行全量测试，0 FAILED。更新 PROGRESS.md，继续簇 C。

---

### 簇 C：规则引擎

文件：`backend/core/agent_rules.py`

所有阈值从 `constants.py` 引用，禁止硬编码数字。

```python
def evaluate_overdue_payments(db) -> list[dict]:
    """
    查询合同（status=active，已约定回款日期但未收到款项）。
    逾期 >= OVERDUE_PAYMENT_HIGH_RISK_DAYS：priority=high
    逾期 >= OVERDUE_PAYMENT_WARNING_DAYS：priority=medium
    返回格式：[{suggestion_type, priority, title, content,
               suggested_action, action_params, _raw: {...}}]
    按实际 v1.x 回款字段名适配，字段名以 PROGRESS.md 记录为准。
    """

def evaluate_profit_anomaly(db) -> list[dict]:
    """
    最近 3 个月完成项目（status=completed）。
    毛利率 = (收入 - 直接成本 - 外包成本) / 收入
    低于 PROFIT_ANOMALY_THRESHOLD_RATE：priority=medium
    """

def evaluate_milestone_risk(db) -> list[dict]:
    """
    milestones 表中 status != completed 且：
      逾期（due_date < today）：priority=high
      即将到期（0 ~ MILESTONE_RISK_DAYS 天内）：priority=medium
    suggested_action = create_reminder
    """

def evaluate_cashflow_warning(db) -> list[dict]:
    """
    读取现金流预测表（按 PROGRESS.md 实际表名）。
    CASHFLOW_WARNING_DAYS 天内净现金流为负：priority=high。
    表不存在时返回空列表，不报错，记录 DEBUG 日志。
    """

def evaluate_task_delay(db, project_id: int = None) -> list[dict]:
    """
    tasks 中 due_date < today 且 status != completed。
    超期 >= TASK_DELAY_WARNING_DAYS 天：priority=medium。
    project_id 非 None 时只查该项目。
    """

def evaluate_change_impact(db, project_id: int) -> list[dict]:
    """
    requirement_changes / change_orders 中 status=pending。
    项目 status=active 时：priority=high，suggested_action=none。
    """

def run_business_decision_rules(db) -> list[dict]:
    """
    组合：overdue_payments + profit_anomaly + milestone_risk + cashflow_warning
    返回合并列表，按 priority 排序（high 在前）。
    """

def run_project_management_rules(db, project_id: int) -> list[dict]:
    """组合：task_delay(project_id) + change_impact(project_id)"""

def build_rule_plain_text(suggestion: dict) -> str:
    """将单条建议转为纯文本，格式固定，不依赖 LLM。"""
```

#### C.1 测试文件 `tests/test_agent_rules.py`

```python
# test_overdue_payment_high_risk_detected → FR-2001
# test_overdue_payment_medium_risk_detected → FR-2001
# test_overdue_payment_no_risk_skipped → FR-2001
# test_profit_anomaly_below_threshold → FR-2001
# test_profit_anomaly_above_threshold_skipped → FR-2001
# test_milestone_risk_overdue → FR-2001
# test_milestone_risk_upcoming → FR-2001
# test_milestone_no_risk_skipped → FR-2001
# test_cashflow_warning_triggered → FR-2001
# test_cashflow_table_missing_returns_empty → FR-2001
# test_task_delay_detected → FR-2001
# test_task_delay_with_project_id_filter → FR-2001
# test_change_impact_pending_change_detected → FR-2001
# test_run_business_decision_rules_sorted_by_priority → FR-2001
# test_run_project_management_rules_combined → FR-2001
# test_build_rule_plain_text_no_llm → FR-2001
```

运行全量测试，0 FAILED。更新 PROGRESS.md，继续簇 D。

---

### 簇 D：LLM Provider 抽象层（三档）⚠️ R3 核心修正簇

文件：`backend/core/llm_client.py`

#### D.1 架构：工厂模式

```python
import os, json, re, logging
from abc import ABC, abstractmethod
from backend.core.constants import (
    LLM_PROVIDER_LOCAL, LLM_PROVIDER_API, LLM_PROVIDER_NONE,
    OLLAMA_TIMEOUT_SECONDS, OLLAMA_HEALTH_CHECK_TIMEOUT,
    API_PROVIDER_TIMEOUT_SECONDS, API_PROVIDER_HEALTH_CHECK_TIMEOUT,
    LLM_PARSE_MAX_RETRIES, LLM_PARSE_EXTRACT_BRACKETS,
    FEEDBACK_WEIGHT_RULES, FEEDBACK_CONTEXT_MAX_RECORDS,
)

logger = logging.getLogger(__name__)
```

#### D.2 JSON 解析增强策略（R3 新增，三档共用）

```python
def _try_parse_llm_json(raw_text: str) -> list[dict] | None:
    """
    三步解析策略，任一步成功立即返回，全部失败返回 None。

    Step 1 - 直接解析：
      json.loads(raw_text.strip())
      成功则返回。

    Step 2 - 括号提取（LLM_PARSE_EXTRACT_BRACKETS=True 时执行）：
      用正则提取第一个 [...] 之间的内容（含嵌套），再 json.loads。
      正则：re.search(r'\[.*\]', raw_text, re.DOTALL)
      成功则返回。

    Step 3 - 返回 None（触发重试或降级）。

    此函数不记录日志，由调用方决定日志策略。
    """


def _build_retry_prompt(suggestions: list[dict]) -> str:
    """
    构建简化重试 prompt（比主 prompt 更简单，减少小模型格式漂移）。
    只包含：
    - 简短指令：只输出 JSON 数组
    - 一个 few-shot 示例（固定，不依赖当前 suggestions）
    - 当前 suggestions 的 title 列表（不含 content，减少 token）
    格式要求：[{"id": <序号>, "enhanced_content": "<描述>"}]
    """
```

#### D.3 BaseLLMProvider 与三档实现

```python
class BaseLLMProvider(ABC):
    @abstractmethod
    def is_available(self) -> bool: ...

    @abstractmethod
    def _call_llm(self, prompt: str, retry_prompt: str) -> list[dict] | None:
        """
        子类实现具体 LLM 调用。
        返回解析后的 JSON 列表，或 None（表示调用/解析失败）。
        实现要求：
        1. 调用 LLM，获取原始文本
        2. _try_parse_llm_json(raw_text)
        3. 若返回 None 且 LLM_PARSE_MAX_RETRIES > 0：
           - 用 retry_prompt 重试一次
           - _try_parse_llm_json(retry_raw_text)
           - 仍为 None 则记录 WARNING(LLM_PARSE_FAILED) 并返回 None
        4. 返回解析结果（成功）或 None（最终失败）
        不抛异常。
        """

    def enhance_suggestions(self, suggestions: list[dict], context: dict) -> list[dict]:
        """
        通用增强流程（三档共用，子类不覆盖此方法）：
        1. 构建主 prompt（含 few-shot 示例 + context 摘要 + suggestions JSON）
        2. 构建 retry_prompt（_build_retry_prompt）
        3. result = self._call_llm(prompt, retry_prompt)
        4. result 为 None：返回原始 suggestions（source 不变），记录已在 _call_llm 中完成
        5. result 非 None：将 enhanced_content 写入对应 suggestion.content，source 改为 provider 标识
        6. 返回 suggestions（不抛异常）
        """

    def get_model_label(self) -> str: ...


class NullProvider(BaseLLMProvider):
    """
    none 档。is_available 返回 False。
    enhance_suggestions 返回原始 suggestions，source 保持 'rule'。
    _call_llm 不实现（不会被调用）。
    """


class OllamaProvider(BaseLLMProvider):
    """
    local 档。模型由 .env LLM_LOCAL_MODEL 配置。

    is_available：
      GET {LLM_LOCAL_BASE_URL}/api/tags，超时 OLLAMA_HEALTH_CHECK_TIMEOUT 返回 False。
      异常静默，记录 DEBUG。

    _call_llm：
      使用 requests.post 调用 Ollama HTTP API（/api/chat），
      超时 OLLAMA_TIMEOUT_SECONDS。
      ⚠️ 不使用 ollama Python SDK 的 chat() 函数（不支持标准 timeout 参数）。
      ⚠️ 使用 requests 直接调用，timeout 参数精确可控。
      解析流程按 D.2 执行。
      超时异常：记录 WARNING(OLLAMA_UNAVAILABLE)，返回 None。

    get_model_label：返回 "local:{LLM_LOCAL_MODEL}"
    source 标识：'local'
    """


class ExternalAPIProvider(BaseLLMProvider):
    """
    api 档。endpoint/key/model 由 .env 配置（OpenAI 兼容接口）。

    is_available：
      LLM_API_BASE 或 LLM_API_KEY 为空时直接返回 False。
      否则发送探测请求，超时 API_PROVIDER_HEALTH_CHECK_TIMEOUT 返回 False。

    _call_llm：
      使用 requests.post 调用 LLM_API_BASE，超时 API_PROVIDER_TIMEOUT_SECONDS。
      解析流程按 D.2 执行。
      超时/连接异常：记录 WARNING(API_PROVIDER_UNAVAILABLE)，返回 None。

    get_model_label：返回 "api:{LLM_API_MODEL}"
    source 标识：'api'

    ⚠️ v2.0 约束：此类不实现任何自由问答或报告生成方法，
      enhance_suggestions 是唯一对外方法，继承自 BaseLLMProvider。
    """
```

#### D.4 主 Prompt 模板（硬编码在 `llm_client.py`，不存数据库）

```python
# 主 prompt（含 few-shot 示例，帮助小模型理解输出格式）
ENHANCE_SYSTEM_PROMPT = """你是一人公司经营助手。
根据以下经营建议，用简洁的中文重新描述每条建议，突出最重要的行动信息。

输出格式示例（严格遵守，不输出任何其他内容）：
[{{"id": 0, "enhanced_content": "客户张三的合同款项已逾期45天，建议本周内跟进催款。"}},
 {{"id": 1, "enhanced_content": "A项目毛利率仅11%，低于预期，建议复查外包成本。"}}]

用户历史偏好摘要（请据此调整表述重点）：
{feedback_summary}

要求：只输出 JSON 数组，不输出任何前缀、后缀、说明文字或 markdown 代码块。"""

ENHANCE_USER_PROMPT = """需要描述的经营建议：
{suggestions_json}"""

# 重试 prompt（更简单，减少小模型格式漂移）
ENHANCE_RETRY_SYSTEM_PROMPT = """只输出 JSON 数组，格式：
[{{"id": 0, "enhanced_content": "一句话描述"}}, ...]
不输出任何其他内容。"""

ENHANCE_RETRY_USER_PROMPT = """请为以下建议各写一句话描述：
{titles_json}"""
```

#### D.5 工厂函数与反馈上下文构建

```python
def get_llm_provider() -> BaseLLMProvider:
    """
    读取 .env LLM_PROVIDER（默认 none）。
    不在白名单时记录 WARNING 并返回 NullProvider。
    """


def build_llm_context(db, agent_type: str) -> dict:
    """
    ⚠️ R3 修正：反馈聚合逻辑（精确定义）

    查询步骤：
    1. 从 human_confirmations 读取最近 FEEDBACK_CONTEXT_MAX_RECORDS 条
       inject_to_next_run=1 的记录，按 created_at DESC 排序。

    聚合规则（关键）：
    2. 按 (decision_type, suggestion_type) 分组。
    3. 每组只保留最近一条（created_at 最大的那条）。
    4. 不同组合的记录各保留一条，不重复注入同一组合。
    5. 最终注入条数 = 唯一 (decision_type, suggestion_type) 组合数。

    权重应用：
    6. 对每条保留记录，查 FEEDBACK_WEIGHT_RULES[(decision_type, suggestion_type)]。
       命中：取 priority_nudge 和 note。
       未命中：priority_nudge=0，note=""（仍注入，用于模型感知历史行为）。

    返回格式：
    {
        "agent_type": agent_type,
        "current_date": "YYYY-MM-DD",
        "feedback_summary": [
            {
                "suggestion_type": "overdue_payment",
                "decision": "rejected",
                "note": "用户上次忽略了逾期回款提醒，可能已自行处理",
                "priority_nudge": -1,
            },
            ...
        ]
    }
    inject_to_next_run=0 的记录严格不出现在 feedback_summary 中。
    """
```

#### D.6 测试文件 `tests/test_llm_client.py`

```python
# ── 工厂函数 ──────────────────────────────────────────────
# test_get_provider_none_returns_null_provider → FR-2002
# test_get_provider_local_returns_ollama_provider → FR-2002
# test_get_provider_api_returns_external_provider → FR-2002
# test_get_provider_unknown_falls_back_to_null_with_warning → FR-2002

# ── NullProvider ──────────────────────────────────────────
# test_null_provider_is_available_false → FR-2002
# test_null_provider_enhance_returns_original_unchanged → FR-2002
# test_null_provider_source_remains_rule → FR-2002

# ── JSON 解析增强（_try_parse_llm_json）────────────────────
# test_parse_valid_json_direct → FR-2002
# test_parse_json_with_preamble_extracted_by_brackets → FR-2002
# test_parse_json_with_markdown_fence_extracted → FR-2002
# test_parse_invalid_returns_none → FR-2002

# ── OllamaProvider ────────────────────────────────────────
# test_ollama_provider_available_true（mock requests.get 成功）→ FR-2002
# test_ollama_provider_available_false_on_timeout → FR-2002
# test_ollama_provider_available_false_on_connection_error → FR-2002
# test_ollama_uses_requests_not_sdk（验证调用 requests.post 而非 ollama.chat）→ FR-2002
# test_ollama_enhance_success_first_attempt（mock requests.post）→ FR-2002
# test_ollama_enhance_parse_fail_triggers_retry → FR-2002
# test_ollama_enhance_retry_success → FR-2002
# test_ollama_enhance_retry_fail_returns_original → FR-2002
# test_ollama_enhance_timeout_returns_original_logs_warning → FR-2002
# test_ollama_source_set_to_local_on_success → FR-2002

# ── ExternalAPIProvider ───────────────────────────────────
# test_external_provider_available_false_when_base_empty → FR-2002
# test_external_provider_available_false_when_key_empty → FR-2002
# test_external_provider_enhance_success（mock requests.post）→ FR-2002
# test_external_provider_enhance_parse_fail_triggers_retry → FR-2002
# test_external_provider_enhance_timeout_returns_original → FR-2002
# test_external_provider_source_set_to_api_on_success → FR-2002
# test_external_provider_has_no_freeform_method → FR-2002
#   （断言 ExternalAPIProvider 不存在 ask / query / report 等方法）

# ── 反馈上下文构建（build_llm_context）────────────────────
# test_build_context_includes_inject_true_records → FR-2002
# test_build_context_excludes_inject_false_records → FR-2002
# test_build_context_dedup_same_combination_keeps_latest → FR-2002
#   （同一 decision_type+suggestion_type 出现 3 次，验证只保留最近 1 条）
# test_build_context_different_combinations_all_kept → FR-2002
#   （rejected+overdue 和 accepted+cashflow 各 1 条，验证都出现在 feedback_summary）
# test_build_context_applies_weight_rules_on_match → FR-2002
#   （rejected+overdue_payment → priority_nudge=-1）
# test_build_context_unknown_combo_nudge_zero → FR-2002
# test_build_context_empty_history_returns_empty_summary → FR-2002
```

运行全量测试，0 FAILED。更新 PROGRESS.md，继续簇 E。

---

### 簇 E：Agent 运行 API

文件：`backend/api/v1/agents.py`，`backend/core/agent_service.py`

#### E.1 接口定义

```http
POST /api/v1/agents/business-decision/run
  body: { use_llm: bool = true }
  response: { agent_run_id, status, llm_provider_used, llm_enhanced, suggestions: [...] }

POST /api/v1/agents/project-management/run
  body: { project_id: int, use_llm: bool = true }
  response: { agent_run_id, status, llm_provider_used, llm_enhanced, suggestions: [...] }

GET /api/v1/agents/runs
  query: ?agent_type=&limit=20&offset=0
  response: { runs: [...], total }

GET /api/v1/agents/runs/{id}
  response: { run, suggestions: [...] }

GET /api/v1/agents/suggestions/pending
  response: { suggestions: [...] }
```

#### E.2 核心函数

```python
def run_agent(db, agent_type: str, use_llm: bool = True, project_id: int = None) -> dict:
    """
    1. 检查同类型 status=running → AGENT_ALREADY_RUNNING（409）
    2. 创建 agent_runs（status=running）
    3. 规则引擎计算建议列表
    4. rule_output = JSON 序列化，写入 agent_runs
    5. 若 use_llm=True：
       a. provider = get_llm_provider()
       b. 若非 NullProvider 且 provider.is_available()：
          - context = build_llm_context(db, agent_type)
          - suggestions = provider.enhance_suggestions(suggestions, context)
          - llm_enhanced=1, llm_model=provider.get_model_label()
       c. 否则：llm_enhanced=0，suggestions 保持规则文本
    6. 批量写入 agent_suggestions
    7. agent_runs.status=completed, completed_at=now, llm_provider=provider_type
    8. 返回结果（含 llm_provider_used 字段）
    异常：status=failed, error_message，日志 ERROR，重新抛出
    原子性：steps 2-7 在单次 DB session 中完成
    """
```

#### E.3 测试文件 `tests/test_agent_service.py`

```python
# test_run_business_decision_creates_run_record → FR-2003
# test_run_business_decision_creates_suggestions → FR-2003
# test_run_business_decision_status_completed → FR-2003
# test_run_agent_already_running_returns_409 → FR-2003
# test_run_agent_use_llm_false_skips_provider → FR-2003
# test_run_agent_provider_none_skips_enhancement → FR-2003
# test_run_agent_provider_local_unavailable_uses_rule_text → FR-2003
# test_run_agent_provider_api_unavailable_uses_rule_text → FR-2003
# test_run_agent_provider_local_enhances_content → FR-2003
# test_run_agent_provider_api_enhances_content → FR-2003
# test_run_agent_llm_model_label_written_to_run_record → FR-2003
# test_run_agent_llm_provider_field_written_to_run_record → FR-2003
# test_run_agent_failure_sets_status_failed → FR-2003
# test_run_project_management_requires_project_id → FR-2003
# test_run_project_management_filters_by_project → FR-2003
# test_get_pending_suggestions_returns_only_pending → FR-2003
# test_get_run_detail_includes_suggestions → FR-2003
```

运行全量测试，0 FAILED。更新 PROGRESS.md，继续簇 F。

---

### 簇 F：建议确认与动作执行 API

文件：`backend/api/v1/agent_confirmations.py`，`backend/core/agent_actions_service.py`

#### F.1 接口定义

```http
POST /api/v1/agents/suggestions/{id}/confirm
  body: {
    decision_type: "accepted"|"rejected"|"modified",
    reason_code: str | null,
    free_text_reason: str | null,
    corrected_fields: dict | null,
    user_priority_override: "high"|"medium"|"low"|null,
    inject_to_next_run: bool = true,
    next_review_at: date | null,
  }
  response: { confirmation_id, action_id | null, action_status | null }

GET /api/v1/agents/actions
  query: ?status=&limit=20&offset=0

GET /api/v1/agents/actions/{id}
```

#### F.2 核心函数

```python
def confirm_suggestion(db, suggestion_id: int, payload: dict) -> dict:
    """
    1. 查询 agent_suggestions，status != pending → SUGGESTION_NOT_PENDING（409）
    2. 写入 human_confirmations
    3. 更新 agent_suggestions.status
    4. decision_type in (accepted, modified) 且 suggested_action != none：
       → 创建 agent_actions（pending）→ execute_action(db, action)
    原子性：steps 2-4 在单次 DB session 中完成
    """

def execute_action(db, action: dict) -> dict:
    """
    - create_todo：插入 todos（按 PROGRESS.md 实际表名），source=agent_action
    - create_reminder：插入提醒表（按 PROGRESS.md 实际表名）
    - generate_report：调用 v1.12 render_template，结果存 agent_actions.result
    成功：status=executed, executed_at=now
    失败：status=failed, error_message，日志 ERROR
          不回滚 human_confirmations 和 suggestion 状态
          抛出 ACTION_EXECUTION_FAILED
    """
```

#### F.3 测试文件 `tests/test_agent_confirmations.py`

```python
# test_confirm_accepted_creates_confirmation_record → FR-2004
# test_confirm_accepted_updates_suggestion_status → FR-2004
# test_confirm_accepted_triggers_action_execution → FR-2004
# test_confirm_rejected_no_action → FR-2004
# test_confirm_modified_with_corrected_fields → FR-2004
# test_confirm_non_pending_raises_409 → FR-2004
# test_inject_to_next_run_false_stored → FR-2004
# test_user_priority_override_stored → FR-2004
# test_execute_action_create_todo_inserts_record → FR-2004
# test_execute_action_create_reminder_inserts_record → FR-2004
# test_execute_action_failure_sets_status_failed → FR-2004
# test_execute_action_failure_does_not_rollback_confirmation → FR-2004
# test_confirm_atomic_on_db_error → FR-2004
```

运行全量测试，0 FAILED。更新 PROGRESS.md，继续簇 G。

---

### 簇 G：前端联调

#### G.1 经营决策页（路由：`/agents/business-decision`）

**Provider 状态感知**：
- 根据 `agent_runs.llm_provider` 最近一条记录显示当前模式标签：「规则模式」/「本地 AI 增强」/「云端 AI 增强」
- local Provider 不可用时：标签降级为「规则模式」，提示「本地模型未启动，已使用规则模式」
- api Provider 不可用时：同上，提示「外部 API 不可用，已使用规则模式」

**运行区**：「运行经营分析」按钮 +「启用 AI 增强」开关（默认开）

**建议列表**：
- 按优先级分组（高风险 / 中等风险 / 低优先级）
- 每条：类型标签 / 优先级标签（high=红色）/ 标题 / 内容 / 来源标记（规则/本地AI/云端AI）
- 操作：「接受」「拒绝」「修改后接受」

**确认弹窗字段**：
- reason_code（下拉：不适用 / 已自行处理 / 不认同分析 / 其他）
- free_text_reason（textarea，可选）
- inject_to_next_run（开关，默认开，标签：「记入下次分析参考」）
- next_review_at（日期，可选）

**空态**：
- 无建议：「当前无风险提示，经营状态良好」
- 全部处理：「本次分析已处理完毕」

#### G.2 项目详情页（追加）

- 「项目智能分析」按钮（仅 status=active 显示）
- 触发 POST `/api/v1/agents/project-management/run`（带 project_id）
- 结果弹窗展示，支持就地确认

#### G.3 Agent 运行日志页（路由：`/agents/logs`）

列表字段：运行时间 / Agent 类型 / 状态 / Provider 模式 / 建议数 / LLM 增强状态
展开：建议详情 + 人工确认结果 + inject_to_next_run 值 + 动作执行状态

**此页面是参赛展示闭环的核心视图，llm_provider / llm_model / inject_to_next_run 必须可见。**

#### G.4 Agent 设置页（路由：`/settings/agent`）

- 展示当前 LLM_PROVIDER 配置值（只读）
- local 档：实时检测 Ollama 连接状态
- api 档：展示 LLM_API_BASE（隐藏 key）

#### G.5 验收标准

- [ ] Provider 不可用时不报错，降级后建议正常展示
- [ ] 来源标记（规则/本地AI/云端AI）在建议卡片正确显示
- [ ] inject_to_next_run 开关默认开，关闭后确认记录 inject=0
- [ ] 已处理建议不出现在 pending 列表
- [ ] 运行日志页展示 llm_provider 和 llm_model 字段
- [ ] 项目智能分析仅在 active 项目显示

运行全量测试，0 FAILED。更新 PROGRESS.md，继续簇 H。

---

### 簇 H：全局重构与验证

#### H.1 常量对齐验证（`tests/test_constants_alignment_v200.py`）

```python
# test_agent_type_whitelist_matches_implemented_handlers → NFR-2003
# test_suggestion_types_all_handled_in_rules → NFR-2003
# test_action_types_all_handled_in_execute_action → NFR-2003
# test_decision_types_all_handled_in_confirm_suggestion → NFR-2003
# test_feedback_weight_rules_suggestion_types_subset_of_defined → NFR-2003
# test_provider_whitelist_matches_factory_branches → NFR-2003
```

#### H.2 函数长度约束

所有新增文件函数 ≤ 50 行，`_try_parse_llm_json` 和 `_build_retry_prompt` 作为辅助函数独立存在。

#### H.3 日志覆盖验证

- Ollama 不可用（WARNING + OLLAMA_UNAVAILABLE）
- 外部 API 不可用（WARNING + API_PROVIDER_UNAVAILABLE）
- LLM JSON 解析失败含重试后（WARNING + LLM_PARSE_FAILED）
- 未知 LLM_PROVIDER（WARNING）
- Agent 运行失败（ERROR）
- 动作执行失败（ERROR）
- Agent 运行成功（INFO，含建议数 + provider 信息）

#### H.4 集成测试（`tests/test_agent_integration.py`）

```python
# test_full_flow_provider_none → FR-2005
#   验证 suggestions.source='rule'，llm_enhanced=0

# test_full_flow_provider_local → FR-2005
#   mock OllamaProvider._call_llm 成功，验证 source='local'

# test_full_flow_provider_api → FR-2005
#   mock ExternalAPIProvider._call_llm 成功，验证 source='api'

# test_full_flow_local_unavailable_degrades → FR-2005
#   mock is_available=False，验证 source='rule'，llm_enhanced=0

# test_full_flow_parse_fail_first_retry_success → FR-2005
#   mock _call_llm：第一次返回无效 JSON，第二次（retry_prompt）返回有效 JSON
#   验证最终 source='local'（增强成功）

# test_full_flow_parse_fail_retry_also_fail_degrades → FR-2005
#   mock _call_llm：两次均返回无效 JSON
#   验证 source='rule'，记录 LLM_PARSE_FAILED

# test_feedback_inject_true_appears_in_context → FR-2005
#   confirm inject_to_next_run=1，再次 run，验证 context.feedback_summary 包含该记录

# test_feedback_inject_false_excluded_from_context → FR-2005
#   confirm inject_to_next_run=0，验证 context.feedback_summary 不含该记录

# test_feedback_dedup_same_combo_only_latest_in_context → FR-2005
#   同一 (rejected, overdue_payment) 出现 3 次，验证 feedback_summary 中只有 1 条

# test_feedback_weight_applied_in_context → FR-2005
#   rejected+overdue_payment → context 中该条 priority_nudge=-1
```

#### H.5 最终全量回归

```bash
pytest tests/ -v --tb=short
# 要求 0 FAILED
# 结果写入 PROGRESS.md
```

---

## 四、完成标准

- [ ] 簇 A ~ H 全部状态为 ✅
- [ ] pytest 全量 0 FAILED
- [ ] 三档 Provider 切换集成测试通过
- [ ] OllamaProvider 使用 requests.post 而非 ollama SDK chat()（timeout 可控）
- [ ] JSON 解析三步策略实现：直接解析 → 括号提取 → 重试 → 降级
- [ ] 重试 prompt 比主 prompt 更简单（few-shot + titles only）
- [ ] 反馈聚合：同 (decision_type, suggestion_type) 组合只注入最近一条
- [ ] inject_to_next_run=0 的记录严格不注入 context
- [ ] FEEDBACK_WEIGHT_RULES 命中/未命中逻辑均有测试覆盖
- [ ] ExternalAPIProvider 无 freeform / ask / report 等方法（测试验证）
- [ ] confirm_suggestion 原子事务通过
- [ ] 动作执行失败不回滚确认记录
- [ ] 所有新增错误码已更新到 help_content.py（见附录 B）
- [ ] logs/ 目录本次执行产生了日志文件

---

## 附录 A：Agent 建议 → 动作映射表

| suggestion_type | suggested_action | action_params 说明 |
|-----------------|------------------|--------------------|
| overdue_payment（high） | create_todo | title=催款提醒，due_date=today+3，source_contract_id |
| overdue_payment（medium） | create_reminder | title=回款跟进，remind_at=today+7 |
| profit_anomaly | create_todo | title=利润异常复查，project_id，due_date=today+7 |
| milestone_risk（overdue） | create_reminder | title=里程碑已逾期，milestone_id，remind_at=today |
| milestone_risk（upcoming） | create_reminder | title=里程碑即将到期，remind_at=due_date-1 |
| cashflow_warning | create_todo | title=现金流预警，due_date=today+3 |
| task_delay | create_reminder | title=任务超期，task_id，remind_at=today |
| change_impact | none | 需人工处理，不自动创建动作 |

---

## 附录 B：v2.0 新增错误码帮助内容（追加到 `backend/core/help_content.py`）

```python
"OLLAMA_UNAVAILABLE": {
    "reason": "本地 Ollama 服务未启动或无法访问，系统已自动降级为规则模式，建议内容不受影响。",
    "next_steps": [
        "启动 Ollama：在终端运行 `ollama serve`",
        "确认模型已下载：`ollama pull gemma4:e2b`",
        "若不需要本地 AI 增强，将 .env 中 LLM_PROVIDER 改为 none",
    ],
    "doc_anchor": "ollama-setup",
},
"API_PROVIDER_UNAVAILABLE": {
    "reason": "外部 LLM API 无法访问，系统已自动降级为规则模式，建议内容不受影响。",
    "next_steps": [
        "检查 .env 中 LLM_API_BASE 和 LLM_API_KEY 是否正确",
        "确认网络连接正常",
        "若不需要外部 API，将 LLM_PROVIDER 改为 local 或 none",
    ],
    "doc_anchor": "api-provider-setup",
},
"LLM_PARSE_FAILED": {
    "reason": "AI 模型返回的内容经解析和重试后仍无法识别，系统已降级为规则文本输出。",
    "next_steps": [
        "此错误通常偶发，重新运行分析即可",
        "若持续出现，检查 logs/ 目录中的详细错误信息",
        "可将 LLM_PROVIDER 改为 none 使用纯规则模式",
    ],
    "doc_anchor": "llm-parse",
},
"AGENT_ALREADY_RUNNING": {
    "reason": "同类型智能体正在运行中，不允许重复触发。",
    "next_steps": [
        "等待当前分析完成后再触发",
        "若长时间无响应，检查 agent_runs 表中 status=running 的记录",
    ],
    "doc_anchor": "agent-concurrent",
},
"SUGGESTION_NOT_PENDING": {
    "reason": "该建议已被处理，不允许重复确认。",
    "next_steps": [
        "在运行日志页查看该建议的历史确认记录",
        "若需重新分析，触发新一次智能体运行",
    ],
    "doc_anchor": "suggestion-status",
},
"ACTION_EXECUTION_FAILED": {
    "reason": "建议对应的动作执行失败，您的确认操作已记录，动作可手动补录。",
    "next_steps": [
        "在「Agent 运行日志」→「动作执行记录」查看失败详情",
        "手动创建对应的待办或提醒",
        "检查 logs/ 目录中的错误信息",
    ],
    "doc_anchor": "action-execution",
},
```

---

## 附录 C：参赛展示路径（7 步完整闭环演示）

1. 打开「经营决策」页，Provider 标签显示「规则模式」，点击「运行经营分析」
2. 展示建议列表（实际经营数据，非 mock），来源标记「规则」
3. 接受一条「逾期回款」建议，确认弹窗勾选「记入下次分析参考」
4. 展示 todos 列表，催款待办已创建（动作执行闭环）
5. 启用 AI 增强，再次运行，展示语言化后的建议（来源标记变为「本地AI」或「云端AI」）
6. 打开「Agent 运行日志」，展示两次运行记录（Provider / LLM增强状态对比）
7. 在第二次运行的 context 摘要中展示「用户通常重视逾期回款提醒（priority_nudge=+1）」，
   说明历史反馈已结构化注入，体现**反馈→优化**闭环可验证性
```
