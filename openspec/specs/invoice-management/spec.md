# invoice-management Specification

## Purpose

独立发票台账管理，支持发票完整生命周期（草稿/开具/已收/已核销/作废），发票编号自动生成，金额累计校验。

## ADDED Requirements

### Requirement: Invoice creation with auto-generated number
The system SHALL support creating invoices with auto-generated invoice numbers in format `INV-YYYYMMDD-序号`. The invoice MUST be associated with an existing contract. The system SHALL calculate tax_amount and total_amount automatically based on amount_excluding_tax and tax_rate.

#### Scenario: Create invoice successfully
- **WHEN** POST /api/v1/invoices with valid contract_id, amount_excluding_tax, tax_rate, invoice_date
- **THEN** system creates invoice with auto-generated invoice_no
- **AND** status defaults to 'draft'
- **AND** tax_amount = round(amount_excluding_tax * tax_rate, 2)
- **AND** total_amount = amount_excluding_tax + tax_amount
- **AND** returns HTTP 201

#### Scenario: Invoice must associate with existing contract
- **WHEN** POST /api/v1/invoices with non-existent contract_id
- **THEN** system returns HTTP 422 with detail "发票必须关联合同"

#### Scenario: Invoice amount cannot be negative
- **WHEN** POST /api/v1/invoices with negative amount_excluding_tax
- **THEN** system returns HTTP 422

#### Scenario: Invoice no increments within same day
- **WHEN** multiple invoices are created on the same day
- **THEN** invoice_no suffix increments from 001, 002, 003...

### Requirement: Invoice cumulative amount validation
The system SHALL validate that the sum of total_amount for all invoices with status != 'cancelled' under the same contract does not exceed the contract amount. This validation SHALL apply during creation and update.

#### Scenario: Create invoice within contract limit accepted
- **WHEN** POST /api/v1/invoices with total_amount <= (contract_amount - existing_invoiced_amount)
- **THEN** system creates invoice successfully

#### Scenario: Create invoice exceeds contract limit rejected
- **WHEN** POST /api/v1/invoices with total_amount > (contract_amount - existing_invoiced_amount)
- **THEN** system returns HTTP 422 with detail "开票金额已超合同金额"

#### Scenario: Cancelled invoice excluded from cumulative calculation
- **WHEN** an invoice with status 'cancelled' exists
- **THEN** its total_amount is excluded from cumulative calculation
- **AND** new invoice can be created up to contract amount

#### Scenario: Update invoice recalculates cumulative amount
- **WHEN** PATCH /api/v1/invoices/{id} with increased total_amount
- **THEN** system validates cumulative amount including updated invoice
- **AND** rejects if exceeds contract amount

### Requirement: Invoice status transition
The system SHALL enforce status transition rules: draft → issued/received/verified/cancelled, issued → received/verified/cancelled, received → verified/cancelled. Verified and cancelled are terminal states.

#### Scenario: Valid transition draft to issued
- **WHEN** POST /api/v1/invoices/{id}/issue with status='draft'
- **THEN** system updates status to 'issued'
- **AND** sets issued_at to current timestamp
- **AND** returns HTTP 200

#### Scenario: Valid transition issued to received
- **WHEN** POST /api/v1/invoices/{id}/receive with status='issued' and received_by provided
- **THEN** system updates status to 'received'
- **AND** sets received_at to current timestamp
- **AND** saves received_by
- **AND** returns HTTP 200

#### Scenario: Valid transition received to verified
- **WHEN** POST /api/v1/invoices/{id}/verify with status='received'
- **THEN** system updates status to 'verified'
- **AND** sets verified_at to current timestamp
- **AND** returns HTTP 200

#### Scenario: Invalid transition rejected
- **WHEN** POST /api/v1/invoices/{id}/receive with status='draft'
- **THEN** system returns HTTP 409 with detail "非法状态流转"

#### Scenario: Terminal state cannot transition
- **WHEN** POST /api/v1/invoices/{id}/issue with status='verified'
- **THEN** system returns HTTP 409 with detail "发票已核销，不可变更"

#### Scenario: Cancel draft invoice
- **WHEN** POST /api/v1/invoices/{id}/cancel with status='draft'
- **THEN** system updates status to 'cancelled'
- **AND** returns HTTP 200

#### Scenario: Cancel verified invoice rejected
- **WHEN** POST /api/v1/invoices/{id}/cancel with status='verified'
- **THEN** system returns HTTP 409 with detail "已核销发票不可作废"

### Requirement: Invoice update constraints
The system SHALL allow updating draft invoices without restrictions. For invoices with status='issued', only notes field can be modified. Verified and cancelled invoices cannot be modified.

#### Scenario: Update draft invoice all fields
- **WHEN** PATCH /api/v1/invoices/{id} with status='draft' and any fields
- **THEN** system updates all fields
- **AND** recalculates tax_amount and total_amount if amount changed
- **AND** returns HTTP 200

#### Scenario: Update issued invoice only notes allowed
- **WHEN** PATCH /api/v1/invoices/{id} with status='issued' and amount_excluding_tax
- **THEN** system returns HTTP 409 with detail "已开具发票只能修改备注"

#### Scenario: Update issued invoice notes success
- **WHEN** PATCH /api/v1/invoices/{id} with status='issued' and notes
- **THEN** system updates notes only
- **AND** returns HTTP 200

#### Scenario: Update verified invoice rejected
- **WHEN** PATCH /api/v1/invoices/{id} with status='verified'
- **THEN** system returns HTTP 409 with detail "已核销发票不可修改"

#### Scenario: Update cancelled invoice rejected
- **WHEN** PATCH /api/v1/invoices/{id} with status='cancelled'
- **THEN** system returns HTTP 409 with detail "已作废发票不可修改"

### Requirement: Invoice deletion constraints
The system SHALL allow deleting draft invoices only. Verified and cancelled invoices cannot be deleted.

#### Scenario: Delete draft invoice success
- **WHEN** DELETE /api/v1/invoices/{id} with status='draft'
- **THEN** system deletes the invoice
- **AND** returns HTTP 204

#### Scenario: Delete issued invoice rejected
- **WHEN** DELETE /api/v1/invoices/{id} with status='issued'
- **THEN** system returns HTTP 409 with detail "已开具发票不可删除"

#### Scenario: Delete verified invoice rejected
- **WHEN** DELETE /api/v1/invoices/{id} with status='verified'
- **THEN** system returns HTTP 409 with detail "已核销发票不可删除"

#### Scenario: Delete cancelled invoice rejected
- **WHEN** DELETE /api/v1/invoices/{id} with status='cancelled'
- **THEN** system returns HTTP 409 with detail "已作废发票不可删除"

### Requirement: Invoice listing and filtering
The system SHALL support listing invoices with pagination, filtering by status, contract_id, date range, ordered by invoice_date DESC.

#### Scenario: List all invoices ordered by date
- **WHEN** GET /api/v1/invoices
- **THEN** system returns invoices ordered by invoice_date DESC
- **AND** includes pagination metadata

#### Scenario: Filter invoices by status
- **WHEN** GET /api/v1/invoices?status=issued
- **THEN** system returns only invoices with status='issued'

#### Scenario: Filter invoices by contract
- **WHEN** GET /api/v1/contracts/{contract_id}/invoices
- **THEN** system returns all invoices associated with the contract

#### Scenario: Filter by date range
- **WHEN** GET /api/v1/invoices?start_date=2024-01-01&end_date=2024-01-31
- **THEN** system returns invoices with invoice_date in range

### Requirement: Invoice summary statistics
The system SHALL provide summary statistics grouped by invoice status, including count and total_amount.

#### Scenario: Get invoice summary
- **WHEN** GET /api/v1/invoices/summary
- **THEN** system returns summary grouped by status
- **AND** includes count and total_amount for each status
- **AND** supports optional date range filtering

### Requirement: Invoice type enumeration
The system SHALL support invoice types: standard (增值税专用发票), ordinary (增值税普通发票), electronic (电子发票), small_scale (小规模纳税人).

#### Scenario: Create invoice with valid type
- **WHEN** POST /api/v1/invoices with invoice_type='standard'
- **THEN** system creates invoice with specified type

#### Scenario: Default invoice type is standard
- **WHEN** POST /api/v1/invoices without invoice_type
- **THEN** system defaults invoice_type to 'standard'

#### Scenario: Invalid invoice type rejected
- **WHEN** POST /api/v1/invoices with invoice_type='invalid'
- **THEN** system returns HTTP 422
