## ADDED Requirements

### Requirement: v1.6 database migration for quotation module
系统 SHALL 提供迁移脚本 `backend/migrations/v1_6_migrate.py`，创建 quotations / quotation_items / quotation_changes 三张新表，为 contracts 表新增 quotation_id 字段，并建立索引和外键约束。迁移 MUST 保留所有已有数据。

#### Scenario: New tables created
- **WHEN** v1.6 迁移执行完成
- **THEN** quotations / quotation_items / quotation_changes 三张表全部存在

#### Scenario: All indexes created
- **WHEN** v1.6 迁移执行完成
- **THEN** 以下索引全部存在：idx_quotations_customer_id / idx_quotations_project_id / idx_quotations_status / idx_quotations_valid_until / idx_quotation_items_quotation_id / idx_quotation_items_sort_order / idx_quotation_changes_quotation_id / idx_contracts_quotation_id

#### Scenario: Migration preserves row counts
- **WHEN** v1.6 迁移执行完成
- **THEN** customers / projects / contracts 行数与迁移前一致

#### Scenario: Migration preserves existing field values
- **WHEN** v1.6 迁移执行完成
- **THEN** 随机抽样记录的所有原有字段值与迁移前快照一致

#### Scenario: Contracts quotation_id field added
- **WHEN** v1.6 迁移执行完成
- **THEN** contracts 表存在 quotation_id 列
- **AND** 已有记录的 quotation_id 为 NULL

#### Scenario: Foreign key constraints enforced
- **WHEN** 设置 quotations.customer_id 为不存在的客户 ID
- **THEN** 数据库外键约束生效

#### Scenario: Quotation items cascade delete
- **WHEN** 删除报价单
- **THEN** 关联的 quotation_items 记录同步删除

#### Scenario: Quote number unique constraint
- **WHEN** 插入重复的 quote_no
- **THEN** UNIQUE 约束生效，拒绝插入
