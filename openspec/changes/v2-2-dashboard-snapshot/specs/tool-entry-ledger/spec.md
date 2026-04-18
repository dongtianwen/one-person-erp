## ADDED Requirements

### Requirement: Tool entries table schema
系统 SHALL 创建 tool_entries 工具入口台账表，记录动作-工具-状态-回填。

#### Scenario: Tool entries table structure
- **WHEN** 数据库 schema 创建
- **THEN** tool_entries 表 SHALL 存在，包含字段：id, action_name, tool_name, status, callback_note, created_at, updated_at

#### Scenario: Status whitelist
- **WHEN** 查看 TOOL_ENTRY_STATUS_WHITELIST
- **THEN** 包含 "pending", "in_progress", "completed", "failed"

### Requirement: Tool entries CRUD API
系统 SHALL 提供工具入口台账的 REST API 端点。

#### Scenario: Create tool entry
- **WHEN** POST /api/v1/tool-entries 传入 action_name, tool_name
- **THEN** 创建记录，初始 status=pending

#### Scenario: List tool entries
- **WHEN** GET /api/v1/tool-entries?status=&limit=20&offset=0
- **THEN** 返回台账数组和 total 总数

#### Scenario: Update tool entry status
- **WHEN** PATCH /api/v1/tool-entries/{id}/status 传入 status 和可选 callback_note
- **THEN** 更新 status 和 callback_note

#### Scenario: Delete tool entry
- **WHEN** DELETE /api/v1/tool-entries/{id}
- **THEN** 返回 { deleted: true }

### Requirement: Tool entry status transition
工具入口台账 SHALL 支持状态流转。

#### Scenario: Valid transition
- **WHEN** status 从 pending → in_progress → completed 或 pending → failed
- **THEN** 更新成功

#### Scenario: Invalid transition
- **WHEN** status 从 completed → pending
- **THEN** 抛出 TOOL_ENTRY_INVALID_TRANSITION 错误
