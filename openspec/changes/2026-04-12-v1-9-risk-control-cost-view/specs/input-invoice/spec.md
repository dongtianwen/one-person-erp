## ADDED Requirements

### Requirement: Input invoice CRUD
系统 SHALL 支持进项发票（供应商开出的成本票）的创建、查询、更新、删除。每个条目包含 invoice_no（必填）、vendor_name（必填）、invoice_date、amount_excluding_tax（不得为负）、tax_rate（默认 0.13）、tax_amount（自动计算）、total_amount（自动计算）、category（默认 other）、project_id（可选关联项目）、notes。进项发票 SHALL 使用独立 input_invoices 表，与销项 invoices 表完全独立。

#### Scenario: Create input invoice success
- **WHEN** POST /api/v1/input-invoices 提供完整有效数据
- **THEN** 创建成功，返回 HTTP 200

#### Scenario: Vendor name required
- **WHEN** POST /api/v1/input-invoices 不提供 vendor_name
- **THEN** 返回 HTTP 422

#### Scenario: Invoice no required
- **WHEN** POST /api/v1/input-invoices 不提供 invoice_no
- **THEN** 返回 HTTP 422

#### Scenario: Amount calculation correct
- **WHEN** amount_excluding_tax=10000, tax_rate=0.13
- **THEN** tax_amount=1300.00, total_amount=11300.00

#### Scenario: Amount must be positive
- **WHEN** amount_excluding_tax < 0
- **THEN** 返回 HTTP 422

#### Scenario: Project association optional
- **WHEN** POST /api/v1/input-invoices 不提供 project_id
- **THEN** 创建成功，project_id = NULL

#### Scenario: Update input invoice success
- **WHEN** PUT /api/v1/input-invoices/{invoice_id} 提供有效更新数据
- **THEN** 更新成功

#### Scenario: Delete input invoice success
- **WHEN** DELETE /api/v1/input-invoices/{invoice_id}
- **THEN** 删除成功

#### Scenario: Input invoice not found returns 404
- **WHEN** GET /api/v1/input-invoices/{nonexistent_id}
- **THEN** 返回 HTTP 404

### Requirement: Input invoice separate from output invoices
进项发票 SHALL 使用独立 input_invoices 表，不与销项 invoices 表共用接口或数据。

#### Scenario: Input invoices use separate table from output invoices
- **WHEN** 查询 input_invoices 表
- **THEN** 不包含 invoices 表的任何记录

#### Scenario: No status field on input invoice
- **WHEN** 创建或查询进项发票
- **THEN** 无 status 字段，无状态流转

### Requirement: Input invoice summary
系统 SHALL 提供按日期范围和类别汇总进项发票的接口。

#### Scenario: Input invoice summary by category
- **WHEN** GET /api/v1/input-invoices/summary 指定日期范围
- **THEN** 返回按 category 汇总的金额

### Requirement: Project input invoice total
系统 SHALL 提供获取项目关联进项发票含税总额的接口。

#### Scenario: Project input invoice total correct
- **WHEN** 项目关联了 2 张进项发票，total_amount 分别为 5000 和 3000
- **THEN** 返回 total=8000

### Requirement: Input invoice API endpoints
系统 SHALL 提供 POST/GET/PUT/DELETE /api/v1/input-invoices、GET /api/v1/projects/{project_id}/input-invoices、GET /api/v1/input-invoices/summary 接口。
