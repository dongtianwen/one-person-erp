## ADDED Requirements

### Requirement: Suggestion confirmation API
系统 SHALL 提供建议确认 API，支持接受/拒绝/修改三种决策类型。

#### Scenario: Accept suggestion
- **WHEN** 用户 POST /api/v1/agents/suggestions/{id}/confirm 且 decision_type=accepted
- **THEN** 写入 human_confirmations，suggestion.status 更新为 confirmed，若 suggested_action != none 则创建并执行 agent_actions

#### Scenario: Reject suggestion
- **WHEN** 用户 POST /api/v1/agents/suggestions/{id}/confirm 且 decision_type=rejected
- **THEN** 写入 human_confirmations，suggestion.status 更新为 rejected，不创建 agent_actions

#### Scenario: Modify suggestion
- **WHEN** 用户 POST /api/v1/agents/suggestions/{id}/confirm 且 decision_type=modified 且 corrected_fields 非空
- **THEN** 写入 human_confirmations（含 corrected_fields），suggestion.status 更新为 confirmed，按修改后的内容执行动作

### Requirement: Suggestion status validation
系统 SHALL 校验建议状态，仅 pending 状态的建议可被确认。

#### Scenario: Non-pending suggestion rejected
- **WHEN** 用户尝试确认 status != pending 的建议
- **THEN** 返回 409，错误码 SUGGESTION_NOT_PENDING

### Requirement: Confirmation payload fields
确认请求 SHALL 支持以下字段：decision_type, reason_code, free_text_reason, corrected_fields, user_priority_override, inject_to_next_run, next_review_at。

#### Scenario: Full confirmation payload
- **WHEN** 用户提交完整确认请求（含所有可选字段）
- **THEN** 所有字段均写入 human_confirmations 记录

#### Scenario: inject_to_next_run default true
- **WHEN** 用户未指定 inject_to_next_run
- **THEN** 默认值为 true（记入下次分析参考）

#### Scenario: inject_to_next_run false stored
- **WHEN** 用户关闭 inject_to_next_run 开关
- **THEN** human_confirmations.inject_to_next_run=0

### Requirement: Action auto-execution on acceptance
系统 SHALL 在接受建议且 suggested_action != none 时自动创建并执行对应动作。

#### Scenario: Accepted with auto-action
- **WHEN** 用户接受一条 suggested_action=create_todo 的建议
- **THEN** 创建 agent_actions（pending）并执行 execute_action，插入 todos 记录

#### Scenario: Accepted without action
- **WHEN** 用户接受一条 suggested_action=none 的建议（如 change_impact）
- **THEN** 不创建 agent_actions，仅写入确认记录

### Requirement: Atomic confirmation transaction
confirm_suggestion 操作 SHALL 在单次数据库事务中完成。

#### Scenario: Database error rolls back confirmation
- **WHEN** confirm_suggestion 执行过程中数据库发生错误
- **THEN** human_confirmations 写入和 suggestion 状态更新均回滚
