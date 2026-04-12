## ADDED Requirements

### Requirement: v1.9 database migration
系统 SHALL 创建迁移脚本 backend/migrations/v1_9_migrate.py，新增 fixed_costs 表（id, name, category, amount, period, effective_date, end_date, project_id, notes, created_at, updated_at）、input_invoices 表（id, invoice_no, vendor_name, invoice_date, amount_excluding_tax, tax_rate, tax_amount, total_amount, category, project_id, notes, created_at, updated_at），扩展 customers 表新增 overdue_milestone_count（默认 0）、overdue_amount（默认 0）、risk_level（默认 normal）字段，扩展 projects 表新增 cached_revenue、cached_labor_cost、cached_fixed_cost、cached_input_cost、cached_gross_profit、cached_gross_margin、profit_cache_updated_at 字段。迁移脚本 SHALL 用 PRAGMA table_info 检查字段是否存在再执行 ALTER TABLE。

#### Scenario: Fixed costs table created
- **WHEN** 执行 v1_9_migrate.py
- **THEN** fixed_costs 表存在且字段正确

#### Scenario: Input invoices table created
- **WHEN** 执行 v1_9_migrate.py
- **THEN** input_invoices 表存在且字段正确

#### Scenario: Customers new columns added
- **WHEN** 执行 v1_9_migrate.py
- **THEN** customers 表新增 overdue_milestone_count、overdue_amount、risk_level 字段

#### Scenario: Projects profit cache columns added
- **WHEN** 执行 v1_9_migrate.py
- **THEN** projects 表新增 cached_revenue 等 7 个缓存字段

#### Scenario: All new indexes created
- **WHEN** 执行 v1_9_migrate.py
- **THEN** 7 个新索引存在

#### Scenario: Existing data preserved
- **WHEN** 迁移后验证
- **THEN** 原有表行数和抽样字段值与迁移前快照一致

#### Scenario: Migration idempotent
- **WHEN** 重复执行 v1_9_migrate.py
- **THEN** 不报错，已存在的字段和索引跳过

#### Scenario: Foreign key project_id nullable
- **WHEN** 创建 fixed_costs 或 input_invoices 时不关联项目
- **THEN** project_id = NULL
