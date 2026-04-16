## ADDED Requirements

### Requirement: Structured feedback context building
系统 SHALL 从 human_confirmations 构建结构化反馈上下文，注入 LLM 调用。

#### Scenario: Build context with inject true records
- **WHEN** build_llm_context 被调用且存在 inject_to_next_run=1 的历史记录
- **THEN** feedback_summary 包含这些记录的结构化摘要

#### Scenario: Exclude inject false records
- **WHEN** build_llm_context 被调用且存在 inject_to_next_run=0 的历史记录
- **THEN** feedback_summary 严格不包含这些记录

### Requirement: Feedback deduplication by combination
同一 (decision_type, suggestion_type) 组合 SHALL 只保留最近一条记录注入上下文。

#### Scenario: Same combination keeps latest
- **WHEN** (rejected, overdue_payment) 出现 3 次
- **THEN** feedback_summary 中只有最近 created_at 的 1 条

#### Scenario: Different combinations all kept
- **WHEN** (rejected, overdue_payment) 和 (accepted, cashflow_warning) 各出现 1 次
- **THEN** feedback_summary 中两条都出现

### Requirement: Feedback weight rules application
系统 SHALL 根据 FEEDBACK_WEIGHT_RULES 为每条反馈应用 priority_nudge 和 note。

#### Scenario: Weight rule match
- **WHEN** 反馈组合为 (rejected, overdue_payment) 且在 FEEDBACK_WEIGHT_RULES 中命中
- **THEN** feedback_summary 中该条 priority_nudge=-1，note="用户上次忽略了逾期回款提醒，可能已自行处理"

#### Scenario: Weight rule miss
- **WHEN** 反馈组合不在 FEEDBACK_WEIGHT_RULES 中
- **THEN** priority_nudge=0，note=""（仍注入用于模型感知历史行为）

### Requirement: Feedback context query limit
build_llm_context SHALL 最多查询 FEEDBACK_CONTEXT_MAX_RECORDS（30）条历史记录。

#### Scenario: Query limited to max records
- **WHEN** human_confirmations 中存在 100 条 inject_to_next_run=1 的记录
- **THEN** 只查询最近 30 条进行聚合

### Requirement: Empty history handling
无历史反馈记录时 SHALL 返回空 feedback_summary。

#### Scenario: Empty history
- **WHEN** human_confirmations 中无任何 inject_to_next_run=1 的记录
- **THEN** build_llm_context 返回 feedback_summary=[]

### Requirement: Priority nudge semantics
priority_nudge SHALL 只影响 LLM 上下文中的描述方式，不修改规则引擎的 priority 字段。

#### Scenario: Nudge does not modify rule priority
- **WHEN** 反馈优先级调整 priority_nudge=-1 且规则引擎生成的 suggestion priority=high
- **THEN** suggestion.priority 仍为 high，只在注入 LLM 上下文时描述为「用户上次忽略了...」
