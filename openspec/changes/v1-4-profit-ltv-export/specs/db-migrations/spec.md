## ADDED Requirements

### Requirement: v1.4 database migration for finance_records
系统 SHALL 提供迁移脚本 `backend/migrations/v1_4_migrate.py`，为 finance_records 表新增 related_project_id 字段（INTEGER NULL, REFERENCES projects(id) ON DELETE SET NULL）并创建索引 idx_finance_records_related_project_id。迁移 MUST 保留所有已有数据。

#### Scenario: Migration preserves row counts
- **WHEN** v1.4 迁移执行完成
- **THEN** finance_records 行数与迁移前一致

#### Scenario: Migration preserves existing field values
- **WHEN** v1.4 迁移执行完成
- **THEN** 随机抽样记录的所有原有字段值与迁移前快照一致

#### Scenario: New field defaults to NULL
- **WHEN** v1.4 迁移在已有记录上执行
- **THEN** 所有已有记录的 related_project_id 为 NULL

#### Scenario: Index exists after migration
- **WHEN** v1.4 迁移执行完成
- **THEN** PRAGMA index_list 确认 idx_finance_records_related_project_id 存在

#### Scenario: Foreign key constraint enforced
- **WHEN** 设置 related_project_id 为不存在的项目 ID
- **THEN** 数据库外键约束生效

#### Scenario: Foreign key set null on project delete
- **WHEN** 关联的项目被删除
- **THEN** finance_records.related_project_id 自动设为 NULL
