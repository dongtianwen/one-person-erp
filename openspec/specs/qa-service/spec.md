## ADDED Requirements

### Requirement: Business data context builder
系统 SHALL 提供 `build_qa_context` 函数，从数据库构建固定经营数据包，目标 token 数 ≤ QA_CONTEXT_MAX_TOKENS_ESTIMATE。

#### Scenario: Context contains required data sections
- **WHEN** build_qa_context 被调用
- **THEN** 返回字典包含 finance_summary（近 QA_CONTEXT_MONTHS 个月财务摘要）、active_projects（最多 QA_CONTEXT_MAX_PROJECTS 个）、overdue_contracts、today 字段

#### Scenario: Finance summary covers correct months
- **WHEN** build_qa_context 构建财务摘要
- **THEN** 包含近 QA_CONTEXT_MONTHS 个月的各月收入、支出、毛利率和当前待收款合计

#### Scenario: Active projects limited to max count
- **WHEN** 活跃项目数量超过 QA_CONTEXT_MAX_PROJECTS
- **THEN** 只返回前 QA_CONTEXT_MAX_PROJECTS 个项目，包含 project_name / customer_name / start_date / contract_amount / milestone_completion_rate / pending_amount

#### Scenario: Subquery failure skips section
- **WHEN** 某个子查询（如财务摘要）失败
- **THEN** 跳过该部分数据，记录 WARNING 日志，不抛异常

#### Scenario: All subqueries fail raises error
- **WHEN** 所有子查询均失败
- **THEN** 抛出 QA_CONTEXT_BUILD_FAILED 错误

### Requirement: QA ask endpoint
系统 SHALL 提供 POST /api/v1/qa/ask 接口，接受 question 和 history 参数，返回 answer 和 llm_model。

#### Scenario: Successful question answering
- **WHEN** LLM_PROVIDER=api 且 ExternalAPIProvider 可用，用户发送有效问题
- **THEN** 返回 HTTP 200，包含 answer（字符串）和 llm_model（字符串）

#### Scenario: Non-api provider blocked
- **WHEN** LLM_PROVIDER != api
- **THEN** 返回 HTTP 403，错误码 QA_REQUIRES_API_PROVIDER

#### Scenario: API provider unavailable
- **WHEN** LLM_PROVIDER=api 但 ExternalAPIProvider.is_available() 返回 False
- **THEN** 返回 HTTP 503，错误码 API_PROVIDER_UNAVAILABLE

#### Scenario: History truncated to max turns
- **WHEN** history 超过 QA_MAX_HISTORY_TURNS 轮
- **THEN** 截断最早的轮次，只保留最近 QA_MAX_HISTORY_TURNS 轮

### Requirement: ExternalAPIProvider freeform call
ExternalAPIProvider SHALL 实现 `call_freeform` 方法，接受完整 messages 列表，返回模型原始文本回答。

#### Scenario: Freeform call success
- **WHEN** call_freeform 被调用且 API 可用
- **THEN** 返回模型原始文本回答（非 JSON），超时 API_PROVIDER_TIMEOUT_SECONDS

#### Scenario: Freeform call not on NullProvider
- **WHEN** 审查 NullProvider 类定义
- **THEN** 不存在 call_freeform 方法

#### Scenario: Freeform call not on OllamaProvider
- **WHEN** 审查 OllamaProvider 类定义
- **THEN** 不存在 call_freeform 方法

### Requirement: QA system prompt
系统 SHALL 使用固定 system prompt 注入经营数据，要求 LLM 只基于提供的数据回答。

#### Scenario: System prompt includes context
- **WHEN** ask_question 构建 messages
- **THEN** system message包含 QA_SYSTEM_PROMPT 模板，其中 {context_json} 被替换为 build_qa_context 的 JSON 序列化结果

### Requirement: QA no persistence
问答接口 SHALL 不落库，不记录对话历史。

#### Scenario: No database writes
- **WHEN** ask_question 被调用
- **THEN** 不向任何数据库表写入对话记录
