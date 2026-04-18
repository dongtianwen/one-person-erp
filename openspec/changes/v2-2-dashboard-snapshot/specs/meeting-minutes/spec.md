## ADDED Requirements

### Requirement: Meeting minutes table schema
系统 SHALL 创建 meeting_minutes 纪要表，存储会议纪要记录。

#### Scenario: Minutes table structure
- **WHEN** 数据库 schema 创建
- **THEN** meeting_minutes 表 SHALL 存在，包含字段：id, title, content, project_id, client_id, meeting_date, participants, created_at, updated_at

#### Scenario: Project foreign key
- **WHEN** meeting_minutes 表创建
- **THEN** project_id 引用 projects(id)，ON DELETE SET NULL

#### Scenario: Client foreign key
- **WHEN** meeting_minutes 表创建
- **THEN** client_id 引用 clients(id)，ON DELETE SET NULL

### Requirement: Minutes must associate with project or client
纪要 SHALL 至少关联一个项目或客户。

#### Scenario: Both project and client provided
- **WHEN** 创建纪要且 project_id 和 client_id 都非空
- **THEN** 创建成功

#### Scenario: Only project provided
- **WHEN** 创建纪要且仅 project_id 非空
- **THEN** 创建成功

#### Scenario: Only client provided
- **WHEN** 创建纪要且仅 client_id 非空
- **THEN** 创建成功

#### Scenario: Neither project nor client provided
- **WHEN** 创建纪要且 project_id 和 client_id 都为空
- **THEN** 抛出 MINUTES_ASSOCIATION_REQUIRED 错误

### Requirement: Minutes save triggers snapshot
纪要保存 SHALL 自动触发 entity_snapshot 创建。

#### Scenario: Create triggers snapshot
- **WHEN** 创建纪要成功
- **THEN** 自动调用 create_snapshot(entity_type="minutes", entity_id=新纪要id, content=纪要内容)

#### Scenario: Update triggers snapshot
- **WHEN** 更新纪要内容成功
- **THEN** 自动调用 create_snapshot(entity_type="minutes", entity_id=纪要id, content=新内容)

#### Scenario: Snapshot failure does not block save
- **WHEN** 纪要保存成功但快照创建失败
- **THEN** 纪要仍保存成功，API 返回 success=true + warning_code=SNAPSHOT_CREATE_FAILED

### Requirement: Minutes CRUD API
系统 SHALL 提供会议纪要的 REST API 端点。

#### Scenario: Create minutes
- **WHEN** POST /api/v1/minutes 传入 title, content, project_id/client_id, meeting_date
- **THEN** 创建纪要记录并触发 snapshot

#### Scenario: List minutes
- **WHEN** GET /api/v1/minutes?project_id=&client_id=&limit=20&offset=0
- **THEN** 返回纪要数组和 total 总数

#### Scenario: Get minutes detail
- **WHEN** GET /api/v1/minutes/{id}
- **THEN** 返回纪要详情

#### Scenario: Update minutes
- **WHEN** PUT /api/v1/minutes/{id} 传入更新内容
- **THEN** 更新纪要并触发 snapshot

#### Scenario: Delete minutes
- **WHEN** DELETE /api/v1/minutes/{id}
- **THEN** 返回 { deleted: true }
