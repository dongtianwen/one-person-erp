## ADDED Requirements

### Requirement: Create todo action
execute_action SHALL 支持 create_todo 动作类型，向 todos 表插入记录。

#### Scenario: Create todo from agent action
- **WHEN** execute_action 接收到 action_type=create_todo
- **THEN** 向 todos 表插入记录，source=agent_action，source_id=action.id

#### Scenario: Todo with due date
- **WHEN** action_params 包含 due_date
- **THEN** 插入的 todo 记录 due_date 字段正确设置

### Requirement: Create reminder action
execute_action SHALL 支持 create_reminder 动作类型，向提醒表插入记录。

#### Scenario: Create reminder from agent action
- **WHEN** execute_action 接收到 action_type=create_reminder
- **THEN** 向提醒表插入记录

### Requirement: Generate report action
execute_action SHALL 支持 generate_report 动作类型，调用 v1.12 模板渲染。

#### Scenario: Generate report via template
- **WHEN** execute_action 接收到 action_type=generate_report
- **THEN** 调用 v1.12 render_template，结果写入 agent_actions.result

### Requirement: Action execution failure handling
动作执行失败 SHALL 记录错误但不回滚确认状态。

#### Scenario: Action fails without rollback
- **WHEN** execute_action 执行失败（如表不存在、渲染失败）
- **THEN** agent_actions.status=failed，error_message 写入，human_confirmations 和 suggestion.status 不回滚

#### Scenario: Error logged on failure
- **WHEN** execute_action 执行失败
- **THEN** 日志记录 ERROR 级别，抛出 ACTION_EXECUTION_FAILED

### Requirement: Action query API
系统 SHALL 提供动作记录的查询 API。

#### Scenario: List actions with pagination
- **WHEN** 用户 GET /api/v1/agents/actions?status=executed&limit=20&offset=0
- **THEN** 返回 actions 数组和 total 总数

#### Scenario: Get single action detail
- **WHEN** 用户 GET /api/v1/agents/actions/{id}
- **THEN** 返回动作详情，包括 result 和 error_message
