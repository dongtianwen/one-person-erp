# finance-export Specification

## Purpose

财务数据通用格式导出，支持合同/收款/发票三种类型，批次追溯，会计期间筛选。

## ADDED Requirements

### Requirement: Export batch creation with unique ID
The system SHALL support creating export batches with auto-generated batch_id in format `EXP-YYYYMMDD-HHMMSS-随机6位`. Each export creates a record in export_batches table.

#### Scenario: Create export batch generates unique ID
- **WHEN** POST /api/v1/finance/export
- **THEN** system generates unique batch_id in format EXP-YYYYMMDD-HHMMSS-XXXXXX
- **AND** creates record in export_batches table
- **AND** returns batch_id in response

#### Scenario: Export batch IDs are unique
- **WHEN** multiple export batches are created rapidly
- **THEN** each batch_id is unique
- **AND** no two batches share the same batch_id

### Requirement: Export to generic Excel format
The system SHALL support exporting contracts, payments, and invoices to generic Excel/CSV format. The export file SHALL be saved to exports/ directory with filename format `{export_type}_{target_format}_{batch_id}.xlsx`.

#### Scenario: Export contracts to Excel
- **WHEN** POST /api/v1/finance/export with export_type='contracts' and target_format='generic'
- **THEN** system generates Excel file with columns: 合同编号, 合同名称, 客户名称, 合同金额, 签订日期, 会计期间, 关联报价单
- **AND** saves file to exports/ directory
- **AND** returns batch_id and file_path

#### Scenario: Export payments to Excel
- **WHEN** POST /api/v1/finance/export with export_type='payments' and target_format='generic'
- **THEN** system generates Excel file with columns: 收款日期, 收款金额, 收款方式, 客户名称, 关联合同, 关联发票, 会计期间, 对账状态, 备注
- **AND** saves file to exports/ directory
- **AND** updates exported records with export_batch_id and accounting_period

#### Scenario: Export invoices to Excel
- **WHEN** POST /api/v1/finance/export with export_type='invoices' and target_format='generic'
- **THEN** system generates Excel file with columns: 发票编号, 发票类型, 开票日期, 客户名称, 不含税金额, 税率, 税额, 价税合计, 关联合同, 发票状态
- **AND** saves file to exports/ directory

#### Scenario: Export with invalid type rejected
- **WHEN** POST /api/v1/finance/export with export_type='invalid'
- **THEN** system returns HTTP 422

### Requirement: Export by accounting period
The system SHALL support filtering exports by accounting_period in format YYYY-MM. When exporting by period, the system SHALL calculate and mark accounting_period for each exported record.

#### Scenario: Export by accounting period
- **WHEN** POST /api/v1/finance/export with accounting_period='2024-01'
- **THEN** system filters records where date field falls in 2024-01
- **AND** calculates period_start and period_end as 2024-01-01 and 2024-01-31
- **AND** marks exported records with accounting_period='2024-01'

#### Scenario: Export by date range
- **WHEN** POST /api/v1/finance/export with start_date='2024-01-01' and end_date='2024-01-15'
- **THEN** system filters records where date field is in range
- **AND** calculates and marks accounting_period for each record based on its date

#### Scenario: Invalid accounting period format rejected
- **WHEN** POST /api/v1/finance/export with accounting_period='2024/01'
- **THEN** system returns HTTP 422 with detail "会计期间格式必须为 YYYY-MM"

### Requirement: Export batch tracking
The system SHALL record each export batch in export_batches table with batch_id, export_type, target_format, accounting_period, start_date, end_date, record_count, file_path, and created_at.

#### Scenario: Export batch record created successfully
- **WHEN** POST /api/v1/finance/export completes
- **THEN** system creates export_batches record with:
  - batch_id: unique identifier
  - export_type: contracts/payments/invoices
  - target_format: generic (or other)
  - accounting_period: YYYY-MM or NULL
  - start_date: filter start date
  - end_date: filter end date
  - record_count: number of exported records
  - file_path: path to exported file or NULL if failed
  - created_at: timestamp

#### Scenario: Export failure records NULL file_path
- **WHEN** export file creation fails
- **THEN** system creates export_batches record with file_path=NULL
- **AND** logs error details

### Requirement: Export batch listing and retrieval
The system SHALL support listing export batches ordered by created_at DESC, and retrieving batch details by batch_id.

#### Scenario: List export batches
- **WHEN** GET /api/v1/finance/export/batches
- **THEN** system returns batches ordered by created_at DESC
- **AND** includes pagination metadata

#### Scenario: Get batch detail
- **WHEN** GET /api/v1/finance/export/batches/{batch_id}
- **THEN** system returns batch details
- **AND** returns HTTP 404 if batch_id not found

### Requirement: Export file download
The system SHALL support downloading exported files by batch_id.

#### Scenario: Download existing file
- **WHEN** GET /api/v1/finance/export/download/{batch_id} with existing file
- **THEN** system returns file as download
- **AND** sets appropriate Content-Type header

#### Scenario: Download missing file returns 404
- **WHEN** GET /api/v1/finance/export/download/{batch_id} with file_path=NULL
- **THEN** system returns HTTP 404 with detail "导出文件不存在"

### Requirement: Target format validation
The system SHALL only support 'generic' format in this version. Other formats (kingdee, yoyo, chanjet) SHALL return HTTP 400.

#### Scenario: Generic format accepted
- **WHEN** POST /api/v1/finance/export with target_format='generic'
- **THEN** system proceeds with export

#### Scenario: Unsupported format returns 400
- **WHEN** POST /api/v1/finance/export with target_format='kingdee'
- **THEN** system returns HTTP 400 with detail "不支持的导出格式"

#### Scenario: Map to non-generic format raises NotImplementedError
- **WHEN** map_to_finance_format is called with target_format != 'generic'
- **THEN** function raises NotImplementedError

### Requirement: Finance records export marking
When exporting payments, the system SHALL update exported finance_records with export_batch_id and accounting_period.

#### Scenario: Payment export marks records
- **WHEN** POST /api/v1/finance/export with export_type='payments'
- **THEN** system updates exported finance_records with:
  - export_batch_id: the generated batch_id
  - accounting_period: calculated period
- **AND** operation is atomic (all or nothing)

#### Scenario: Atomic export rollback on failure
- **WHEN** export fails after marking some records
- **THEN** system rolls back all changes
- **AND** no records are partially marked

### Requirement: Export record count accuracy
The export_batches.record_count SHALL accurately reflect the number of records exported.

#### Scenario: Record count matches exported rows
- **WHEN** export completes
- **THEN** record_count equals number of rows in exported file
- **AND** record_count equals number of marked finance_records (for payments export)
