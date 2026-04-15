# 数标云管 v2.1 — Claude Code 执行指令（R2 修正版）

## 项目目标

在 v2.0 AI 智能体闭环层基础上，新增三项增强分析能力：

1. **经营数据自由问答**（仅 api 档可用）
2. **深度报告生成**（项目复盘 + 客户分析，扩展 v1.12 模板系统）
3. **交付/质检智能体升级**（规则检查 + LLM 语言化，复用 v2.0 四张表）

本版本不做：多轮对话落库、LLM 自主判断交付物内容质量、报告自动推送、多人协作。

---

## 零、关键语义边界定义（实施前必读，禁止跳过）

### 0.1 三项能力的精确定位

```text
自由问答（QA）：
  - 用户输入自然语言问题 → 系统注入固定经营数据包 → api Provider 回答
  - 仅 LLM_PROVIDER=api 时前端显示入口，local/none 不显示
  - 多轮对话由前端维护 messages 数组，后端每次接收完整历史，不落库
  - 不做：问题路由识别、按问题类型动态选择数据、跨会话历史

深度报告（Report）：
  - 扩展 v1.12 模板系统，新增 report_project / report_customer 两种模板类型
  - 结构：Jinja2 固定框架（代码拼装结构性数据）+ LLM 填充分析段落变量
  - 存储：新建 reports 表，独立于 quotations/contracts
  - api 为正式主力模式，local 作为降级兜底，none 仅填占位文本
  - 不做：报告自动推送、多人协作

交付/质检智能体（Delivery QC）：
  - 复用 v2.0 四张 Agent 表，新增 AGENT_TYPE_DELIVERY_QC
  - 规则层：检查交付包完整性（有无模型版本、验收记录、数据集版本）
  - LLM 层：质检报告语言化 + 缺失项描述增强（同 v2.0 语言增强模式）
  - 不做：LLM 自主判断交付物内容质量，不读取实际文件内容
```

### 0.2 自由问答的 Provider 限制（精确）

```python
# 前端判断规则：
# LLM_PROVIDER=api 且 ExternalAPIProvider.is_available()：显示问答入口
# 其他情况：显示"此功能需接入外部模型，请在设置中配置 api Provider"
# 不显示降级版本，不用 local/none 尝试回答

# 后端守卫：
# POST /api/v1/qa/ask 在 LLM_PROVIDER != api 时返回 HTTP 403（QA_REQUIRES_API_PROVIDER）
# 双重保护，前端判断 + 后端守卫
```

### 0.3 报告生成的 LLM 分工（精确）

```python
# 代码负责（不依赖 LLM）：
#   - 从 DB 读取结构性数据（工时、里程碑、收款、变更记录等）
#   - 拼装 Jinja2 context dict（所有数值、日期、列表字段）
#   - 渲染模板中非 LLM 变量的部分

# LLM 负责（仅填充以下变量）：
#   - project_report：analysis_summary / risk_retrospective / improvement_suggestions
#   - customer_report：value_assessment / relationship_summary / next_action_suggestions

# LLM 填充失败（任意 Provider 不可用）：
#   - 分析变量填入占位文本："（AI 分析不可用，请手动补充）"
#   - 报告仍然生成，结构完整，不阻断
```

### 0.4 错误码边界

```python
# QA_REQUIRES_API_PROVIDER：问答接口在非 api 档被调用——403
# QA_CONTEXT_BUILD_FAILED：经营数据上下文构建失败——500，日志 ERROR
# REPORT_TYPE_NOT_SUPPORTED：报告类型不在白名单——400
# REPORT_ENTITY_NOT_FOUND：目标实体（project/customer）不存在——404
# REPORT_LLM_FILL_FAILED：LLM 段落填充失败——降级为占位文本，不阻断，日志 WARNING
# DELIVERY_QC_NO_PACKAGE：质检目标交付包不存在——404
```

### 0.5 v1.12 模板系统扩展边界

```python
# TEMPLATE_TYPE_WHITELIST 新增（追加，不修改已有）：
#   "report_project" / "report_customer"

# reports 表与 templates 表关联：
#   reports.template_id → templates.id（ON DELETE SET NULL，快照不受影响）

# reports 表与 quotations/contracts 表完全独立：
#   不共享 generated_content 字段，不相互影响

# 报告版本规则：重新生成不覆盖旧记录，而是新增版本记录；默认展示 is_latest=1
```

---

## 一、前置检查

```bash
pytest tests/ -v --tb=short  # 要求 0 FAILED

# 确认 v2.0 四张表存在：agent_runs / agent_suggestions / agent_actions / human_confirmations
# 确认 v1.12 templates 表存在
# 确认 v1.11 delivery_packages / model_versions / dataset_versions 表存在
# 记录 delivery_packages 实际字段到 PROGRESS.md（质检规则依赖）

# 确认 .env 存在以下字段（v2.0 已有）：
# LLM_PROVIDER / LLM_API_BASE / LLM_API_KEY / LLM_API_MODEL

# 检查 constants.py 中 TEMPLATE_TYPE_WHITELIST 当前值，记录到 PROGRESS.md
```

PROGRESS.md 初始化：

```markdown
## v2.1 执行进度

| 簇 | 描述 | 状态 |
|----|------|------|
| A  | 数据库迁移（reports 表 + 常量扩展） | ⏳ |
| B  | 自由问答后端 | ⏳ |
| C  | 深度报告后端 | ⏳ |
| D  | 交付/质检智能体 | ⏳ |
| E  | 前端联调 | ⏳ |
| F  | 全局重构与验证 | ⏳ |

## 实际字段记录（前置检查后填写）
- delivery_packages 实际字段：[待填写]
- TEMPLATE_TYPE_WHITELIST 当前值：[待填写]
```

---

## 二、全局常量扩展（追加到 `backend/core/constants.py`）

```python
# ── 模板类型（扩展 v1.12 白名单）────────────────────────────
TEMPLATE_TYPE_REPORT_PROJECT = "report_project"
TEMPLATE_TYPE_REPORT_CUSTOMER = "report_customer"

# ── 报告相关 ──────────────────────────────────────────────
REPORT_TYPE_PROJECT = "report_project"
REPORT_TYPE_CUSTOMER = "report_customer"
REPORT_TYPE_WHITELIST = [REPORT_TYPE_PROJECT, REPORT_TYPE_CUSTOMER]

REPORT_STATUS_GENERATING = "generating"
REPORT_STATUS_COMPLETED = "completed"
REPORT_STATUS_FAILED = "failed"

PROJECT_REPORT_LLM_VARS = [
    "analysis_summary",
    "risk_retrospective",
    "improvement_suggestions",
]
CUSTOMER_REPORT_LLM_VARS = [
    "value_assessment",
    "relationship_summary",
    "next_action_suggestions",
]

REPORT_LLM_FALLBACK_TEXT = "（AI 分析不可用，请手动补充）"

# ── Agent 类型（扩展 v2.0 白名单）────────────────────────────
AGENT_TYPE_DELIVERY_QC = "delivery_qc"

# ── 质检建议类型（新增）──────────────────────────────────────
SUGGESTION_TYPE_DELIVERY_MISSING_MODEL = "delivery_missing_model"
SUGGESTION_TYPE_DELIVERY_MISSING_DATASET = "delivery_missing_dataset"
SUGGESTION_TYPE_DELIVERY_MISSING_ACCEPTANCE = "delivery_missing_acceptance"
SUGGESTION_TYPE_DELIVERY_VERSION_MISMATCH = "delivery_version_mismatch"
SUGGESTION_TYPE_DELIVERY_EMPTY_PACKAGE = "delivery_empty_package"
SUGGESTION_TYPE_DELIVERY_UNBOUND_PROJECT = "delivery_unbound_project"

# ── 自由问答 ──────────────────────────────────────────────
QA_CONTEXT_MONTHS = 3
QA_CONTEXT_MAX_PROJECTS = 10
QA_CONTEXT_MAX_TOKENS_ESTIMATE = 2000
QA_MAX_HISTORY_TURNS = 10
```

追加到 `backend/core/error_codes.py`：

```python
ERROR_QA_REQUIRES_API_PROVIDER = "QA_REQUIRES_API_PROVIDER"
ERROR_QA_CONTEXT_BUILD_FAILED = "QA_CONTEXT_BUILD_FAILED"
ERROR_REPORT_TYPE_NOT_SUPPORTED = "REPORT_TYPE_NOT_SUPPORTED"
ERROR_REPORT_ENTITY_NOT_FOUND = "REPORT_ENTITY_NOT_FOUND"
ERROR_REPORT_LLM_FILL_FAILED = "REPORT_LLM_FILL_FAILED"
ERROR_DELIVERY_QC_NO_PACKAGE = "DELIVERY_QC_NO_PACKAGE"
```

---

## 三、执行清单

---

### 簇 A：数据库迁移

#### A.1 新建 reports 表

```sql
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_type VARCHAR(50) NOT NULL,
    entity_id INTEGER NOT NULL,
    entity_type VARCHAR(20) NOT NULL,
    template_id INTEGER NULL REFERENCES templates(id) ON DELETE SET NULL,
    parent_report_id INTEGER NULL REFERENCES reports(id) ON DELETE SET NULL,
    version_no INTEGER NOT NULL DEFAULT 1,
    is_latest INTEGER NOT NULL DEFAULT 1,
    content TEXT NULL,
    llm_filled_vars TEXT NULL,
    llm_provider VARCHAR(20) NULL,
    llm_model VARCHAR(100) NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'generating',
    error_message TEXT NULL,
    generated_at TIMESTAMP NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_reports_entity
    ON reports(entity_type, entity_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_reports_type_status
    ON reports(report_type, status);
```

#### A.2 扩展 constants.py 白名单（只在 constants.py 定义一次，其他文件禁止重复定义）

```python
TEMPLATE_TYPE_WHITELIST = [
    TEMPLATE_TYPE_QUOTATION,
    TEMPLATE_TYPE_CONTRACT,
    TEMPLATE_TYPE_REPORT_PROJECT,
    TEMPLATE_TYPE_REPORT_CUSTOMER,
]

AGENT_TYPE_WHITELIST = [
    AGENT_TYPE_BUSINESS_DECISION,
    AGENT_TYPE_PROJECT_MANAGEMENT,
    AGENT_TYPE_DELIVERY_QC,
]
```

#### A.3 默认报告模板写入（幂等：先查 template_type + is_default=1，存在则跳过）

项目复盘报告默认模板：

```text
项目复盘报告

项目名称：{{ project_name }}
客户：{{ customer_name }}
报告生成日期：{{ generated_date }}

━━━━━━━━━━━━━━━━━━━━━━━━

一、项目概况

项目周期：{{ start_date }} 至 {{ end_date }}（共 {{ duration_days }} 天）
合同金额：¥{{ contract_amount }}
实际收款：¥{{ received_amount }}
{% if pending_amount and pending_amount > 0 %}待收款：¥{{ pending_amount }}
{% endif %}

━━━━━━━━━━━━━━━━━━━━━━━━

二、执行情况

累计工时：{{ total_hours }} 小时
里程碑完成率：{{ milestone_completion_rate }}%
变更单数量：{{ change_count }} 个
验收通过：{{ acceptance_passed }}

━━━━━━━━━━━━━━━━━━━━━━━━

三、财务表现

毛利率：{{ gross_margin_rate }}%
直接成本：¥{{ direct_cost }}
{% if outsource_cost and outsource_cost > 0 %}外包成本：¥{{ outsource_cost }}
{% endif %}

━━━━━━━━━━━━━━━━━━━━━━━━

四、综合分析

{{ analysis_summary }}

━━━━━━━━━━━━━━━━━━━━━━━━

五、风险复盘

{{ risk_retrospective }}

━━━━━━━━━━━━━━━━━━━━━━━━

六、改进建议

{{ improvement_suggestions }}
```

客户分析报告默认模板：

```text
客户分析报告

客户名称：{{ customer_name }}
报告生成日期：{{ generated_date }}

━━━━━━━━━━━━━━━━━━━━━━━━

一、合作概况

合作项目数：{{ project_count }}
累计合同金额：¥{{ total_contract_amount }}
累计收款金额：¥{{ total_received_amount }}
{% if total_pending > 0 %}当前待收款：¥{{ total_pending }}
{% endif %}首次合作：{{ first_project_date }}
最近合作：{{ last_project_date }}

━━━━━━━━━━━━━━━━━━━━━━━━

二、客户价值

LTV 估算：¥{{ ltv_estimate }}
平均项目金额：¥{{ avg_project_amount }}
回款准时率：{{ payment_on_time_rate }}%

━━━━━━━━━━━━━━━━━━━━━━━━

三、价值评估

{{ value_assessment }}

━━━━━━━━━━━━━━━━━━━━━━━━

四、关系摘要

{{ relationship_summary }}

━━━━━━━━━━━━━━━━━━━━━━━━

五、下一步建议

{{ next_action_suggestions }}
```

#### A.4 测试文件 `tests/test_migration_v210.py`

```python
# test_reports_table_exists → NFR-2101
# test_reports_entity_index_exists → NFR-2101
# test_reports_type_status_index_exists → NFR-2101
# test_template_type_whitelist_includes_report_types → NFR-2101
# test_agent_type_whitelist_includes_delivery_qc → NFR-2101
# test_default_project_report_template_inserted → NFR-2101
# test_default_customer_report_template_inserted → NFR-2101
# test_report_templates_idempotent_no_duplicate → NFR-2101
# test_existing_tables_row_counts_unchanged → NFR-2101
# test_existing_tables_fields_unchanged → NFR-2101
```

运行全量测试，0 FAILED。更新 PROGRESS.md，继续簇 B。

---

### 簇 B：自由问答后端

文件：`backend/core/qa_service.py`，`backend/api/v1/qa.py`

#### B.1 经营数据上下文构建

```python
def build_qa_context(db) -> dict:
    """
    构建固定经营数据包，目标 token 数 <= QA_CONTEXT_MAX_TOKENS_ESTIMATE。

    包含以下数据（结构化，不做自然语言化）：
    1. 近 QA_CONTEXT_MONTHS 个月财务摘要：
       - 各月收入、支出、毛利率
       - 当前待收款合计
    2. 活跃项目列表（status=active，最多 QA_CONTEXT_MAX_PROJECTS 个）：
       - project_name / customer_name / start_date / contract_amount
       - milestone_completion_rate（里程碑完成率）
       - pending_amount（待收款）
    3. 当前逾期合同（复用 v2.0 规则引擎已有逻辑）
    4. 当前时间：today

    任何子查询失败：跳过该部分数据，记录 WARNING，不抛异常。
    全部子查询失败：抛出 QA_CONTEXT_BUILD_FAILED。
    """
```

#### B.2 问答接口

```python
# POST /api/v1/qa/ask
# 请求体：
# {
#   "question": str,
#   "history": [
#     {"role": "user", "content": "..."},
#     {"role": "assistant", "content": "..."}
#   ]
# }
# 响应体：{ "answer": str, "llm_model": str }

# 守卫：
# LLM_PROVIDER != api → HTTP 403（QA_REQUIRES_API_PROVIDER）
# ExternalAPIProvider.is_available() == False → HTTP 503（API_PROVIDER_UNAVAILABLE）
```

```python
def ask_question(db, question: str, history: list[dict]) -> dict:
    """
    1. 截断 history 超过 QA_MAX_HISTORY_TURNS 的最早轮次
    2. context = build_qa_context(db)
    3. 构建 messages：system + history + user
    4. 调用 ExternalAPIProvider.call_freeform(messages)
    5. 返回 { answer, llm_model }
    不落库，不记录对话历史。
    """
```

#### B.3 ExternalAPIProvider 新增方法

```python
def call_freeform(self, messages: list[dict]) -> str:
    """
    自由问答专用调用，接受完整 messages 列表（含 system/history/user）。
    超时 API_PROVIDER_TIMEOUT_SECONDS。
    返回模型原始文本回答（非 JSON，不做格式校验）。
    失败：记录 WARNING，抛出异常（由调用方处理）。
    仅 ExternalAPIProvider 实现。
    """
```

#### B.4 问答 System Prompt

```python
QA_SYSTEM_PROMPT = """你是一人公司经营助手。
以下是当前经营数据（JSON 格式），请基于这些真实数据回答用户的问题。

经营数据：
{context_json}

回答要求：
1. 只基于以上数据回答，不要编造数据
2. 回答简洁，重点突出，适合一人公司老板快速决策
3. 如果数据不足以回答问题，明确说明缺少哪些信息
4. 使用中文回答"""
```

#### B.5 测试文件 `tests/test_qa_service.py`

```python
# test_build_qa_context_returns_required_keys → FR-2101
# test_build_qa_context_finance_summary_correct_months → FR-2101
# test_build_qa_context_active_projects_limit → FR-2101
# test_build_qa_context_subquery_failure_skips_not_raises → FR-2101
# test_build_qa_context_all_fail_raises_context_failed → FR-2101
# test_ask_question_requires_api_provider → FR-2101
# test_ask_question_history_truncated_to_max_turns → FR-2101
# test_ask_question_success（mock ExternalAPIProvider.call_freeform）→ FR-2101
# test_ask_question_provider_unavailable_returns_503 → FR-2101
# test_call_freeform_not_on_null_provider → FR-2101
# test_call_freeform_not_on_ollama_provider → FR-2101
```

运行全量测试，0 FAILED。更新 PROGRESS.md，继续簇 C。

---

### 簇 C：深度报告后端

文件：`backend/core/report_service.py`，`backend/api/v1/reports.py`

#### C.1 接口定义

```http
POST /api/v1/reports/generate
  body: { report_type: str, entity_id: int, template_id: int | null }
  response: { report_id, status, content | null }

GET /api/v1/reports
  query: ?entity_type=&entity_id=&limit=10&offset=0
  response: { reports: [...], total }

GET /api/v1/reports/{id}
  response: { report detail + content }

DELETE /api/v1/reports/{id}
  response: { deleted: true }
```

#### C.2 核心函数

```python
def build_project_report_context(db, project_id: int) -> dict:
    """
    从以下表读取数据（按 v1.x 实际字段名，字段名记录在 PROGRESS.md）：
    - projects：名称、起止日期
    - customers：客户名称
    - contracts：合同金额
    - finance_records：收款记录（计算 received_amount / pending_amount）
    - work_hour_logs：累计工时
    - milestones：里程碑完成率
    - change_orders / requirement_changes：变更单数量
    - acceptances：验收通过情况
    - fixed_costs + outsourcing：直接成本、外包成本
    返回 context dict，所有变量在 Jinja2 模板中可用。
    project_id 不存在：抛出 REPORT_ENTITY_NOT_FOUND。
    """


def build_customer_report_context(db, customer_id: int) -> dict:
    """
    从以下表读取：
    - customers：客户名称
    - projects：合作项目列表（count / 首次 / 最近）
    - contracts：合同金额汇总
    - finance_records：收款汇总、待收款
    - LTV 数据（复用 v1.4 LTV 计算函数）
    - 回款准时率（计算：实际收款日 vs 约定收款日）
    customer_id 不存在：抛出 REPORT_ENTITY_NOT_FOUND。
    """


def fill_llm_vars(db, report_type: str, context: dict) -> dict:
    """
    对 PROJECT_REPORT_LLM_VARS 或 CUSTOMER_REPORT_LLM_VARS 中的每个变量：
    1. 构建针对该变量的 prompt（携带 context 数据）
    2. provider = get_llm_provider()
    3. 若 provider 可用：
       - 调用 provider._call_llm_single_var(var_name, context)
       - 成功：写入 context[var_name]
       - 失败：context[var_name] = REPORT_LLM_FALLBACK_TEXT，记录 WARNING(REPORT_LLM_FILL_FAILED)
    4. 若 provider 不可用：context[var_name] = REPORT_LLM_FALLBACK_TEXT
    返回填充后的 context。不抛异常。
    """


def generate_report(db, report_type: str, entity_id: int, template_id: int = None) -> dict:
    """
    1. report_type 不在白名单：抛出 REPORT_TYPE_NOT_SUPPORTED
    2. 创建 reports 记录（status=generating）
    3. 获取 template（template_id 指定 or 该类型默认模板）
       模板不存在：抛出 TEMPLATE_NOT_FOUND
    4. build_*_report_context(db, entity_id)
    5. fill_llm_vars(db, report_type, context)
    6. render_template(template.content, context, required_vars=[])
       （复用 v1.12 render_template，报告无必填变量校验，LLM vars 已有兜底）
    7. 若已存在同 entity 的最新报告：旧报告 is_latest=0；新报告 parent_report_id 指向旧报告；version_no = old.version_no + 1
    8. 更新 reports：content=结果 / llm_filled_vars=JSON / status=completed / generated_at=now / is_latest=1
    9. 返回 report
    任何步骤异常：status=failed, error_message，日志 ERROR
    """
```

#### C.3 LLM 单变量填充辅助方法

```python
# 在 BaseLLMProvider 相关实现中，允许给支持报告的 Provider 实现：

def _call_llm_single_var(self, var_name: str, context: dict) -> str | None:
    """
    针对单个报告变量生成文本。
    输入：变量名 + 完整 context
    输出：纯文本字符串（非 JSON），或 None（失败）
    不做 JSON 解析，直接返回模型输出文本。
    超时：返回 None。
    """
```

变量 prompt 模板：

```python
REPORT_VAR_PROMPTS = {
    "analysis_summary": "根据以下项目数据，用 2-3 句话总结项目整体执行情况：\n{context_summary}",
    "risk_retrospective": "根据以下项目数据，指出项目中出现的主要风险和问题：\n{context_summary}",
    "improvement_suggestions": "根据以下项目数据，给出 2-3 条具体的改进建议：\n{context_summary}",
    "value_assessment": "根据以下客户数据，评估该客户的商业价值（1-2 句话）：\n{context_summary}",
    "relationship_summary": "根据以下客户数据，描述合作关系特点（1-2 句话）：\n{context_summary}",
    "next_action_suggestions": "根据以下客户数据，给出 1-2 条下一步跟进建议：\n{context_summary}",
}
```

#### C.4 测试文件 `tests/test_report_service.py`

```python
# test_build_project_context_returns_required_fields → FR-2102
# test_build_project_context_entity_not_found → FR-2102
# test_build_customer_context_returns_required_fields → FR-2102
# test_build_customer_context_entity_not_found → FR-2102
# test_fill_llm_vars_provider_none_uses_fallback → FR-2102
# test_fill_llm_vars_provider_unavailable_uses_fallback → FR-2102
# test_fill_llm_vars_success_writes_content → FR-2102
# test_fill_llm_vars_partial_fail_fills_fallback_for_failed → FR-2102
# test_generate_report_type_not_supported → FR-2102
# test_generate_report_creates_record → FR-2102
# test_generate_report_status_completed → FR-2102
# test_generate_report_content_not_null → FR-2102
# test_generate_report_failure_sets_status_failed → FR-2102
# test_generate_report_llm_fill_failed_still_completes → FR-2102
# test_report_uses_default_template_when_not_specified → FR-2102
# test_report_recreates_with_version_increment → FR-2102
```

运行全量测试，0 FAILED。更新 PROGRESS.md，继续簇 D。

---

### 簇 D：交付/质检智能体

文件：`backend/core/agent_rules.py`（追加），`backend/core/agent_service.py`（扩展）

#### D.1 质检规则函数（追加到 agent_rules.py）

```python
def evaluate_delivery_package(db, package_id: int) -> list[dict]:
    """
    对指定 delivery_packages 记录执行完整性检查。
    package_id 不存在：抛出 DELIVERY_QC_NO_PACKAGE。

    规则列表（按 v1.11 实际字段名，字段名以 PROGRESS.md 记录为准）：

    规则 1 - 模型版本缺失：
      delivery_packages 未关联任何 model_versions（通过 package_model_versions 表）
      → suggestion_type=delivery_missing_model, priority=high
      → suggested_action=create_todo（补充模型版本）

    规则 2 - 数据集版本缺失：
      delivery_packages 未关联任何 dataset_versions（通过 package_dataset_versions 表）
      → suggestion_type=delivery_missing_dataset, priority=medium
      → suggested_action=create_todo（补充数据集版本）

    规则 3 - 验收记录缺失：
      delivery_packages.status != accepted 且无对应 acceptances 记录
      → suggestion_type=delivery_missing_acceptance, priority=high
      → suggested_action=create_reminder（跟进验收）

    规则 4 - 版本不一致：
      package_model_versions 关联的 model_version.status = deprecated
      → suggestion_type=delivery_version_mismatch, priority=high
      → suggested_action=create_todo（更新模型版本）

    规则 5 - 交付包为空：
      交付包无任何关键内容或附件
      → suggestion_type=delivery_empty_package, priority=high
      → suggested_action=create_todo

    规则 6 - 交付包未绑定项目：
      交付包未绑定有效项目
      → suggestion_type=delivery_unbound_project, priority=high
      → suggested_action=create_todo

    返回空列表 = 质检通过，无问题。
    """


def run_delivery_qc_rules(db, package_id: int) -> list[dict]:
    """调用 evaluate_delivery_package，返回结果列表。"""
```

#### D.2 扩展 run_agent 支持 delivery_qc

```python
# 在 agent_service.py 的 run_agent 函数中，扩展 agent_type 路由：
# AGENT_TYPE_DELIVERY_QC → run_delivery_qc_rules(db, package_id)
# package_id 从调用参数传入（类比 project_id）

# POST /api/v1/agents/delivery-qc/run
# body: { package_id: int, use_llm: bool = true }
# response: { agent_run_id, status, llm_provider_used, llm_enhanced, suggestions: [...] }
```

#### D.3 测试文件 `tests/test_delivery_qc.py`

```python
# test_evaluate_package_missing_model → FR-2103
# test_evaluate_package_missing_dataset → FR-2103
# test_evaluate_package_missing_acceptance → FR-2103
# test_evaluate_package_version_mismatch → FR-2103
# test_evaluate_package_empty → FR-2103
# test_evaluate_package_unbound_project → FR-2103
# test_evaluate_package_all_pass_returns_empty → FR-2103
# test_evaluate_package_not_found_raises_404 → FR-2103
# test_run_delivery_qc_agent_creates_run_record → FR-2103
# test_run_delivery_qc_suggestions_written → FR-2103
# test_run_delivery_qc_with_llm_enhancement → FR-2103
# test_run_delivery_qc_without_llm_uses_rule_text → FR-2103
# test_delivery_qc_confirm_creates_action → FR-2103
```

运行全量测试，0 FAILED。更新 PROGRESS.md，继续簇 E。

---

### 簇 E：前端联调

#### E.1 经营助手问答页（路由：`/assistant/qa`）

**入口显示条件**：

* `LLM_PROVIDER=api` 且 api Provider 可用：显示完整问答界面
* 其他情况：显示说明页“此功能需接入外部模型，请在设置中配置 API Provider”，不显示输入框

**界面结构**：

* 顶部：当前使用模型标签（`llm_model` 字段值）
* 主区：对话气泡列表（用户/助手交替，前端维护，不持久化）
* 底部：输入框 + 发送按钮
* 刷新/离开页面：对话历史清空（前端状态，不恢复）

**交互规则**：

* 发送时：将完整 history + 当前 question 发给后端
* 等待响应时：输入框禁用，显示 loading
* 响应返回：追加助手气泡，恢复输入
* 失败：显示“请求失败，请重试”，不追加气泡

#### E.2 报告页面（两个入口）

**项目详情页（已有）追加**：

* 「生成项目复盘报告」按钮（仅 status=completed 的项目显示）
* 点击：POST `/api/v1/reports/generate`（report_type=report_project）
* 生成中：按钮 loading
* 生成后：弹窗展示报告内容（white-space: pre-wrap）+ 「历史报告」入口

**客户详情页（已有）追加**：

* 「生成客户分析报告」按钮
* 逻辑同上（report_type=report_customer）

**报告历史弹窗**：

* 列表：生成时间 / Provider / 状态 / 版本号
* 点击查看：展示 content
* 删除：调用 DELETE `/api/v1/reports/{id}`

#### E.3 交付包详情页（已有）追加

* 「运行质检分析」按钮（任何状态的交付包均可触发）
* 点击：POST `/api/v1/agents/delivery-qc/run`（body 带 package_id）
* 结果弹窗：展示质检建议列表，支持就地确认
* 质检通过（建议列表为空）：显示「✅ 质检通过，交付包完整」

#### E.4 Agent 设置页扩展（`/settings/agent`）

* 新增「自由问答」区域：

  * 显示当前 api Provider 状态
  * 若未配置：展示配置指引（填写 LLM_API_BASE / LLM_API_KEY / LLM_API_MODEL）
  * ⚠️ key 字段只写不读（输入后存入 .env，不回显）

#### E.5 验收标准

* [ ] 非 api 档时，问答页显示说明而非输入框
* [ ] 问答历史刷新后清空，无持久化
* [ ] 报告生成中 loading 状态正确
* [ ] LLM 填充失败时报告仍生成，分析段落显示占位文本
* [ ] 质检通过时显示成功提示而非空列表
* [ ] 交付包质检建议可通过 v2.0 确认流程处理
* [ ] 报告版本号在历史弹窗中可见

运行全量测试，0 FAILED。更新 PROGRESS.md，继续簇 F。

---

### 簇 F：全局重构与验证

#### F.1 常量对齐验证（`tests/test_constants_alignment_v210.py`）

```python
# test_template_type_whitelist_includes_all_report_types → NFR-2103
# test_agent_type_whitelist_includes_delivery_qc → NFR-2103
# test_report_type_whitelist_matches_build_context_functions → NFR-2103
# test_suggestion_type_delivery_types_handled_in_qc_rules → NFR-2103
# test_report_llm_vars_handled_in_fill_llm_vars → NFR-2103
# test_call_freeform_only_on_external_provider → NFR-2103
# test_llm_single_var_not_on_null_provider → NFR-2103
```

#### F.2 函数长度约束

所有新增文件函数 ≤ 50 行。`build_project_report_context` 和 `build_customer_report_context` 若超长，提取子函数。

#### F.3 日志覆盖验证

* LLM 段落填充失败（WARNING + REPORT_LLM_FILL_FAILED）
* 报告生成失败（ERROR）
* 质检 package 不存在（WARNING）
* QA context 子查询失败（WARNING）
* QA context 全部失败（ERROR + QA_CONTEXT_BUILD_FAILED）

#### F.4 集成测试（`tests/test_v210_integration.py`）

```python
# test_full_report_flow_provider_none → FR-2104
#   生成项目复盘报告，LLM_PROVIDER=none，验证分析段落为 fallback 文本，报告 status=completed

# test_full_report_flow_provider_local → FR-2104
#   mock 本地 Provider 的单变量填充，验证分析段落被填充

# test_full_report_flow_llm_partial_failure → FR-2104
#   第一个 LLM var 成功，第二个失败，验证报告仍 completed，失败 var 为 fallback

# test_full_delivery_qc_flow_with_missing_model → FR-2104
#   创建无模型版本的交付包，运行质检，验证 delivery_missing_model 建议生成

# test_full_delivery_qc_confirm_creates_todo → FR-2104
#   确认质检建议，验证 todo 创建

# test_qa_endpoint_blocked_on_local_provider → FR-2104
#   mock LLM_PROVIDER=local，POST /qa/ask，验证返回 403

# test_qa_history_truncation → FR-2104
#   传入超过 QA_MAX_HISTORY_TURNS 轮历史，验证截断后发送给 LLM
```

#### F.5 最终全量回归

```bash
pytest tests/ -v --tb=short
# 要求 0 FAILED
# 结果写入 PROGRESS.md
```

---

## 四、完成标准

* [ ] 簇 A ~ F 全部状态为 ✅
* [ ] pytest 全量 0 FAILED
* [ ] 自由问答在 local/none 档返回 403（双重保护验证）
* [ ] 问答历史截断逻辑通过测试
* [ ] 报告 LLM 填充失败时仍生成（fallback 文本）
* [ ] 报告重新生成新增版本，不覆盖旧版本
* [ ] 质检规则覆盖六类问题（missing_model / missing_dataset / missing_acceptance / version_mismatch / empty_package / unbound_project）
* [ ] 质检建议可通过 v2.0 confirm_suggestion 流程处理
* [ ] call_freeform 仅存在于 ExternalAPIProvider（测试验证）
* [ ] _call_llm_single_var 按实现约束仅在支持该能力的 Provider 中可用
* [ ] TEMPLATE_TYPE_WHITELIST 和 AGENT_TYPE_WHITELIST 只在 constants.py 定义一次
* [ ] 所有新增错误码已更新到 help_content.py（见附录 B）
* [ ] logs/ 目录本次执行产生了日志文件

---

## 附录 A：项目复盘报告变量来源表

| 变量名                       | 来源                                | 类型         |
| ------------------------- | --------------------------------- | ---------- |
| project_name              | projects.name                     | 代码拼装       |
| customer_name             | customers.name                    | 代码拼装       |
| generated_date            | today                             | 代码拼装       |
| start_date                | projects.start_date               | 代码拼装       |
| end_date                  | projects.end_date 或 completed_at  | 代码拼装       |
| duration_days             | 计算值                               | 代码拼装       |
| contract_amount           | contracts.amount                  | 代码拼装       |
| received_amount           | finance_records 汇总                | 代码拼装       |
| pending_amount            | contract_amount - received_amount | 代码拼装       |
| total_hours               | work_hour_logs 汇总                 | 代码拼装       |
| milestone_completion_rate | milestones 完成率计算                  | 代码拼装       |
| change_count              | change_orders count               | 代码拼装       |
| acceptance_passed         | acceptances 结果                    | 代码拼装       |
| gross_margin_rate         | 毛利率计算                             | 代码拼装       |
| direct_cost               | fixed_costs 汇总                    | 代码拼装       |
| outsource_cost            | outsourcing 汇总                    | 代码拼装       |
| analysis_summary          | —                                 | **LLM 填充** |
| risk_retrospective        | —                                 | **LLM 填充** |
| improvement_suggestions   | —                                 | **LLM 填充** |

---

## 附录 B：v2.1 新增错误码帮助内容（追加到 `backend/core/help_content.py`）

```python
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
"DELIVERY_QC_NO_PACKAGE": {
    "reason": "指定的交付包不存在，无法执行质检。",
    "next_steps": [
        "确认 package_id 正确",
        "前往交付包列表确认该包是否存在",
    ],
    "doc_anchor": "delivery-qc",
},
```
