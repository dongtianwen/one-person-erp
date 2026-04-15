## ADDED Requirements

### Requirement: Agent run lifecycle management
系统 SHALL 管理 Agent 运行的完整生命周期，包括创建、运行中、完成、失败状态流转。

#### Scenario: Create new agent run
- **WHEN** 用户触发经营分析或项目分析
- **THEN** 系统创建 agent_runs 记录，status=running，created_at=当前时间

#### Scenario: Complete agent run successfully
- **WHEN** 规则引擎和可选 LLM 增强均执行完毕
- **THEN** agent_runs.status 更新为 completed，completed_at 写入当前时间

#### Scenario: Agent run fails
- **WHEN** 规则引擎或 LLM 调用抛出未捕获异常
- **THEN** agent_runs.status 更新为 failed，error_message 写入错误信息，日志记录 ERROR 级别

### Requirement: Concurrent run prevention
同类型 Agent SHALL 不允许同时运行多个实例。

#### Scenario: Prevent duplicate run
- **WHEN** 用户触发 business_decision 运行且存在 status=running 的 business_decision 记录
- **THEN** 系统返回 409，错误码 AGENT_ALREADY_RUNNING

#### Scenario: Allow different agent types to run concurrently
- **WHEN** business_decision 正在运行，用户触发 project_management
- **THEN** project_management 正常运行，不受影响

### Requirement: Agent run query API
系统 SHALL 提供 Agent 运行记录的查询 API。

#### Scenario: List agent runs with pagination
- **WHEN** 用户 GET /api/v1/agents/runs?agent_type=business_decision&limit=20&offset=0
- **THEN** 返回 runs 数组和 total 总数，按 created_at 降序排列

#### Scenario: Get single run detail with suggestions
- **WHEN** 用户 GET /api/v1/agents/runs/{id}
- **THEN** 返回 run 详情及其关联的 suggestions 列表

### Requirement: Pending suggestions query
系统 SHALL 提供待确认建议的查询 API。

#### Scenario: Get all pending suggestions
- **WHEN** 用户 GET /api/v1/agents/suggestions/pending
- **THEN** 返回所有 status=pending 的 suggestions，按优先级排序（high 在前）

### Requirement: Agent run record schema
agent_runs 表 SHALL 包含以下字段：id, agent_type, trigger_type, status, llm_provider, rule_output, llm_enhanced, llm_model, context_snapshot, error_message, created_at, completed_at。

#### Scenario: Run record contains provider info
- **WHEN** Agent 运行完成且 LLM_PROVIDER=local 且可用
- **THEN** llm_provider=local，llm_enhanced=1，llm_model=local:gemma4:e2b
