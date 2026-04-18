## ADDED Requirements

### Requirement: Entity snapshots table schema
系统 SHALL 创建 entity_snapshots 统一快照表，支持多实体类型的版本留痕。

#### Scenario: Snapshots table structure
- **WHEN** 数据库 schema 创建
- **THEN** entity_snapshots 表 SHALL 存在，包含字段：id, entity_type, entity_id, version_no, content, is_latest, created_at

#### Scenario: Entity type index
- **WHEN** 数据库 schema 创建
- **THEN** idx_snapshots_entity 索引 SHALL 存在于 (entity_type, entity_id, created_at DESC)

#### Scenario: Latest snapshot index
- **WHEN** 数据库 schema 创建
- **THEN** idx_snapshots_latest 索引 SHALL 存在于 (entity_type, entity_id, is_latest) WHERE is_latest = 1

#### Scenario: Entity type whitelist
- **WHEN** 查看 SNAPSHOT_ENTITY_TYPE_WHITELIST
- **THEN** 包含 "report", "minutes", "template"

### Requirement: Create snapshot
系统 SHALL 提供 `create_snapshot` 函数，为指定实体创建新版本快照。

#### Scenario: First snapshot
- **WHEN** 为某实体创建首个快照
- **THEN** version_no = 1, is_latest = 1

#### Scenario: Subsequent snapshot
- **WHEN** 为某实体创建后续快照
- **THEN** 旧快照 is_latest 置为 0，新快照 version_no = 旧版本 + 1, is_latest = 1

#### Scenario: Concurrent snapshot creation
- **WHEN** 并发为同一实体创建快照
- **THEN** 使用原子操作 `UPDATE ... SET is_latest=False WHERE entity_type=? AND entity_id=? AND is_latest=True` 确保 is_latest 不冲突

### Requirement: Get latest snapshot
系统 SHALL 提供 `get_latest_snapshot` 函数，获取指定实体的最新快照。

#### Scenario: Entity has snapshots
- **WHEN** 查询某实体的最新快照且存在快照
- **THEN** 返回 is_latest=1 的快照记录

#### Scenario: Entity has no snapshots
- **WHEN** 查询某实体的最新快照且不存在快照
- **THEN** 返回 None

### Requirement: Get snapshot history
系统 SHALL 提供 `get_snapshot_history` 函数，获取指定实体的快照历史列表。

#### Scenario: History ordered by version
- **WHEN** 查询某实体的快照历史
- **THEN** 按 version_no DESC 排序返回所有快照

### Requirement: Save with snapshot
系统 SHALL 提供 `save_with_snapshot` 函数，保存实体内容并自动触发快照创建。

#### Scenario: Save succeeds and snapshot created
- **WHEN** 保存实体内容成功
- **THEN** 自动调用 create_snapshot 为该实体创建快照

#### Scenario: Save succeeds but snapshot fails
- **WHEN** 保存实体内容成功但快照创建失败
- **THEN** 主业务不回滚，API 返回 success=true + warning_code=SNAPSHOT_CREATE_FAILED

### Requirement: Get version diff
系统 SHALL 提供 `get_version_diff` 函数，返回两个版本快照的内容供对比。

#### Scenario: Both versions exist
- **WHEN** 请求两个版本的 diff 且两个版本都存在
- **THEN** 返回 { version_a: { version_no, content }, version_b: { version_no, content } }

#### Scenario: Version not found
- **WHEN** 请求的版本号不存在
- **THEN** 抛出 SNAPSHOT_VERSION_NOT_FOUND 错误
