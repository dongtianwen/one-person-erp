## ADDED Requirements

### Requirement: Finance records related_project_id field
finance_records 表 SHALL 新增 `related_project_id` 字段（INTEGER NULL），建立外键约束引用 projects(id)，ON DELETE SET NULL。SHALL 创建索引 idx_finance_records_related_project_id。

#### Scenario: Field defaults to NULL after migration
- **WHEN** 迁移完成后查询已有 finance_records
- **THEN** 所有记录的 related_project_id 为 NULL

#### Scenario: Index exists after migration
- **WHEN** 迁移完成后通过 PRAGMA index_list 检查
- **THEN** idx_finance_records_related_project_id 索引存在

#### Scenario: Foreign key constraint enforced
- **WHEN** 设置 related_project_id 为不存在的项目 ID
- **THEN** 数据库拒绝写入

#### Scenario: Set NULL on project delete
- **WHEN** 关联的项目被删除
- **THEN** finance_records.related_project_id 自动设为 NULL

### Requirement: Finance API supports related_project_id
POST 创建接口和 PUT/PATCH 更新接口 SHALL 支持 `related_project_id` 字段。传入时验证项目 ID 存在，不存在返回 HTTP 422。可传 null 以清空关联。

#### Scenario: Valid project ID accepted
- **WHEN** 创建或更新财务记录时传入有效的 related_project_id
- **THEN** 系统保存关联关系

#### Scenario: Invalid project ID returns 422
- **WHEN** 创建或更新财务记录时传入不存在的 related_project_id
- **THEN** 返回 HTTP 422

#### Scenario: Null clears association
- **WHEN** 更新财务记录时传入 related_project_id=null
- **THEN** 系统清除项目关联

### Requirement: Frontend shows project selector for expenses only
前端财务收支录入页 SHALL 仅在支出类型记录时显示"关联项目"下拉选择字段（选填）。收入类型不显示此字段。

#### Scenario: Expense type shows project selector
- **WHEN** 用户选择支出类型
- **THEN** "关联项目"下拉出现，显示项目列表

#### Scenario: Income type hides project selector
- **WHEN** 用户从支出切换为收入类型
- **THEN** "关联项目"字段消失，值清空，payload 不含此字段

#### Scenario: Optional field allows empty submission
- **WHEN** 用户不选择关联项目直接提交支出记录
- **THEN** 记录正常创建，related_project_id 为 NULL

### Requirement: Migration data preservation
迁移脚本 `backend/migrations/v1_4_migrate.py` SHALL 保留所有已有数据。迁移前记录快照，迁移后验证行数一致、抽样数据一致。

#### Scenario: Total row count unchanged after migration
- **WHEN** 迁移完成后
- **THEN** finance_records 总行数与迁移前一致

#### Scenario: Existing fields unchanged after migration
- **WHEN** 迁移完成后
- **THEN** 随机抽样 5 条记录，所有原有字段值与快照完全一致
