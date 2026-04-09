# finance-management Specification (Delta)

## Purpose

定义 finance_records 表扩展字段，支持发票关联、会计期间标记、导出批次追溯和对账状态。

## MODIFIED Requirements

### Requirement: Finance record creation
系统 SHALL 支持创建收入和支出记录，支出记录必须提供资金来源，特定资金来源需填写结算状态。创建接口 SHALL 支持 `related_project_id`、`invoice_id`、`accounting_period` 可选字段。

#### Scenario: Create income record
- GIVEN 用户已登录
- WHEN 用户创建收入记录
- AND 选择关联合同
- AND 输入金额、分类、描述、发生日期
- THEN 系统创建收入记录
- AND 初始状态为"待确认"
- AND 发票号码唯一性校验（如提供）

#### Scenario: Create record with invoice_id
- **WHEN** POST /api/v1/finance/ with existing invoice_id
- **THEN** system creates record with invoice_id set
- **AND** returns HTTP 200

#### Scenario: Create record with invalid invoice_id returns 422
- **WHEN** POST /api/v1/finance/ with non-existent invoice_id
- **THEN** system returns HTTP 422 with detail "发票不存在"

#### Scenario: Create record with accounting_period
- **WHEN** POST /api/v1/finance/ with accounting_period='2024-01'
- **THEN** system creates record with accounting_period set

#### Scenario: Create income must link to contract
- GIVEN 用户创建收入记录
- WHEN 用户未选择关联合同
- THEN 系统拒绝创建
- AND 提示"收入记录必须关联合同"

### Requirement: Finance record update
系统 SHALL 支持更新财务记录，但有安全限制。已确认记录修改时自动记录变更日志。更新接口 SHALL 支持 `related_project_id`、`invoice_id`、`accounting_period`、`export_batch_id`、`reconciliation_status` 字段修改。

#### Scenario: Update pending finance record
- GIVEN 财务记录状态为"待确认"
- WHEN 用户修改记录信息
- THEN 系统允许修改
- AND 更新修改时间

#### Scenario: Update invoice_id
- **WHEN** PATCH /api/v1/finance/{id} with invoice_id
- **THEN** system validates invoice exists
- **AND** returns HTTP 422 if invoice does not exist
- **AND** accepts NULL to clear association

#### Scenario: Update reconciliation_status
- **WHEN** PATCH /api/v1/finance/{id} with reconciliation_status
- **THEN** system validates status is in allowed values (pending/matched/verified)
- **AND** returns HTTP 422 for invalid status

#### Scenario: Update confirmed record logs changes
- GIVEN 财务记录状态为"已确认"
- WHEN 用户修改记录信息
- THEN 系统允许修改
- AND 自动创建变更日志记录修改前后的字段值
- AND 记录修改时间和操作人

## ADDED Requirements

### Requirement: Reconciliation status enumeration
The finance_records.reconciliation_status field SHALL support values: 'pending', 'matched', 'verified'. The default value SHALL be 'pending'.

#### Scenario: Default reconciliation status is pending
- **WHEN** finance_record is created
- **THEN** reconciliation_status defaults to 'pending'

#### Scenario: Invalid reconciliation status rejected
- **WHEN** PATCH /api/v1/finance/{id} with reconciliation_status='invalid'
- **THEN** system returns HTTP 422

### Requirement: Export batch ID field
The finance_records.export_batch_id field SHALL track which export batch the record was included in. This field SHALL be NULL for unexported records.

#### Scenario: Unexported record has NULL export_batch_id
- **WHEN** finance_record is created
- **THEN** export_batch_id is NULL

#### Scenario: Export sets export_batch_id
- **WHEN** record is included in export batch
- **THEN** export_batch_id is set to the batch_id

### Requirement: Accounting period auto-calculation
When not explicitly provided, the system SHALL calculate accounting_period from transaction_date as YYYY-MM.

#### Scenario: Auto-calculate accounting_period from transaction_date
- **WHEN** POST /api/v1/finance/ with transaction_date='2024-01-15' and no accounting_period
- **THEN** system sets accounting_period='2024-01'

#### Scenario: Explicit accounting_period overrides auto-calculation
- **WHEN** POST /api/v1/finance/ with transaction_date='2024-01-15' and accounting_period='2024-02'
- **THEN** system sets accounting_period='2024-02' (explicit value wins)

### Requirement: Invoice-foreign key constraint
The finance_records.invoice_id field SHALL reference invoices(id) with ON DELETE SET NULL.

#### Scenario: Delete linked invoice sets NULL
- **WHEN** invoice referenced by finance_records is deleted
- **THEN** finance_records.invoice_id is set to NULL
- **AND** the finance_record is not deleted

### Requirement: Reconciliation status independent from invoice status
The reconciliation_status field SHALL be independent from invoices.status. Changing one SHALL NOT affect the other.

#### Scenario: Invoice status change does not affect reconciliation_status
- **WHEN** invoice.status changes from 'issued' to 'verified'
- **THEN** linked finance_records.reconciliation_status remains unchanged

#### Scenario: Reconciliation status change does not affect invoice status
- **WHEN** finance_records.reconciliation_status changes to 'verified'
- **THEN** linked invoice.status remains unchanged
