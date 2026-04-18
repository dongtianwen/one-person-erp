## ADDED Requirements

### Requirement: Leads table schema
系统 SHALL 创建 leads 客户线索台账表，轻量跟进记录。

#### Scenario: Leads table structure
- **WHEN** 数据库 schema 创建
- **THEN** leads 表 SHALL 存在，包含字段：id, source, status, next_action, client_id, project_id, notes, created_at, updated_at

#### Scenario: Client foreign key
- **WHEN** leads 表创建
- **THEN** client_id 引用 clients(id)，ON DELETE SET NULL

#### Scenario: Project foreign key
- **WHEN** leads 表创建
- **THEN** project_id 引用 projects(id)，ON DELETE SET NULL

#### Scenario: Source whitelist
- **WHEN** 查看 LEAD_SOURCE_WHITELIST
- **THEN** 包含 "referral", "website", "event", "cold_outreach", "other"

#### Scenario: Status whitelist
- **WHEN** 查看 LEAD_STATUS_WHITELIST
- **THEN** 包含 "initial_contact", "intent_confirmed", "converted", "invalid"

### Requirement: Leads CRUD API
系统 SHALL 提供客户线索台账的 REST API 端点。

#### Scenario: Create lead
- **WHEN** POST /api/v1/leads 传入 source, status, next_action
- **THEN** 创建线索记录

#### Scenario: List leads
- **WHEN** GET /api/v1/leads?status=&source=&limit=20&offset=0
- **THEN** 返回线索数组和 total 总数

#### Scenario: Get lead detail
- **WHEN** GET /api/v1/leads/{id}
- **THEN** 返回线索详情

#### Scenario: Update lead
- **WHEN** PUT /api/v1/leads/{id} 传入更新内容
- **THEN** 更新线索记录

#### Scenario: Delete lead
- **WHEN** DELETE /api/v1/leads/{id}
- **THEN** 返回 { deleted: true }

### Requirement: Lead status transition
线索 SHALL 支持状态流转。

#### Scenario: Valid transition to intent_confirmed
- **WHEN** status 从 initial_contact → intent_confirmed
- **THEN** 更新成功

#### Scenario: Valid transition to converted
- **WHEN** status 从 intent_confirmed → converted
- **THEN** 更新成功，可选关联 client_id

#### Scenario: Valid transition to invalid
- **WHEN** status 从任意状态 → invalid
- **THEN** 更新成功

#### Scenario: Invalid reverse transition
- **WHEN** status 从 converted → initial_contact
- **THEN** 抛出 LEAD_INVALID_TRANSITION 错误

### Requirement: Lead conversion
线索转化为客户 SHALL 记录关联。

#### Scenario: Convert with client_id
- **WHEN** 线索 status 变更为 converted 且提供 client_id
- **THEN** 记录 client_id 关联

#### Scenario: Convert without client_id
- **WHEN** 线索 status 变更为 converted 且未提供 client_id
- **THEN** 仍允许转换，client_id 为 null
