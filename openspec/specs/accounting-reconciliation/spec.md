# accounting-reconciliation Specification

## Purpose

会计期间对账报表，按自然月统计业务财务数据，支持客户维度分解和未对账记录识别。

## ADDED Requirements

### Requirement: Accounting period date range calculation
The system SHALL calculate period_start and period_end dates for a given accounting_period in format YYYY-MM.

#### Scenario: Calculate period range for January
- **WHEN** get_period_date_range('2024-01')
- **THEN** returns (date(2024,1,1), date(2024,1,31))

#### Scenario: Calculate period range for February leap year
- **WHEN** get_period_date_range('2024-02')
- **THEN** returns (date(2024,2,1), date(2024,2,29))

#### Scenario: Calculate period range for December
- **WHEN** get_period_date_range('2024-12')
- **THEN** returns (date(2024,12,1), date(2024,12,31))

#### Scenario: Invalid period format returns error
- **WHEN** get_period_date_range('2024/01')
- **THEN** raises ValueError

### Requirement: Opening balance calculation
The system SHALL calculate opening_balance as the closing_balance of the previous period. For the first period with data, opening_balance SHALL be zero.

#### Scenario: First period opening balance is zero
- **WHEN** get_opening_balance is called for the first period with data
- **THEN** returns {accounts_receivable: 0.00, unbilled_amount: 0.00, total: 0.00}

#### Scenario: Opening balance equals previous closing
- **WHEN** get_opening_balance('2024-02') and previous period closing is 100000
- **THEN** returns opening_balance total = 100000

### Requirement: Current period activity calculation
The system SHALL calculate current period statistics including: contracts_signed, contracts_amount, invoices_issued, invoices_amount (excluding cancelled), payments_received, payments_amount, invoices_verified, verified_amount.

#### Scenario: Calculate contracts activity
- **WHEN** get_current_period_activity is called
- **THEN** contracts_amount = sum(contracts.amount) where sign_date in period
- **AND** contracts_signed = count of such contracts

#### Scenario: Calculate invoices activity excluding cancelled
- **WHEN** get_current_period_activity is called
- **THEN** invoices_amount = sum(invoices.total_amount) where invoice_date in period AND status != 'cancelled'
- **AND** cancelled invoices are excluded

#### Scenario: Calculate payments activity
- **WHEN** get_current_period_activity is called
- **THEN** payments_amount = sum(finance_records.amount) where transaction_date in period
- **AND** payments_received = count of such records

#### Scenario: Calculate verified invoices
- **WHEN** get_current_period_activity is called
- **THEN** verified_amount = sum(invoices.total_amount) where verified_at in period
- **AND** invoices_verified = count of such invoices

### Requirement: Closing balance calculation
The system SHALL calculate closing_balance as: accounts_receivable = opening_accounts_receivable + current_contracts - current_payments, unbilled_amount = current_contracts - current_invoices.

#### Scenario: Closing balance formula
- **WHEN** get_closing_balance is called
- **THEN** accounts_receivable = opening.accounts_receivable + current.contracts_amount - current.payments_amount
- **AND** unbilled_amount = current.contracts_amount - current.invoices_amount
- **AND** total = accounts_receivable + unbilled_amount

### Requirement: Customer breakdown aggregation
The system SHALL provide per-customer breakdown of current period activity including: contracts_amount_this_period, invoices_amount_this_period, payments_amount_this_period, outstanding_balance.

#### Scenario: Customer breakdown aggregates correctly
- **WHEN** get_customer_breakdown is called
- **THEN** returns list with one entry per customer
- **AND** each includes customer_id, customer_name, and period aggregates
- **AND** outstanding_balance = contracts_amount - payments_amount

#### Scenario: Customer with no activity excluded
- **WHEN** get_customer_breakdown is called
- **THEN** customers with no contracts/invoices/payments in period are excluded

### Requirement: Unreconciled records identification
The system SHALL identify finance_records where contract_id IS NULL as unreconciled records.

#### Scenario: Find unreconciled payment records
- **WHEN** get_unreconciled_records is called
- **THEN** returns finance_records where contract_id IS NULL
- **AND** includes record_id, record_type='payment', amount, transaction_date
- **AND** reason='无匹配合同'

#### Scenario: All records have contract returns empty
- **WHEN** get_unreconciled_records is called and all payments have contract_id
- **THEN** returns empty list

### Requirement: Reconciliation report generation
The system SHALL generate a complete reconciliation report including: accounting_period, period_start, period_end, opening_balance, current_period, closing_balance, breakdown, unreconciled_records.

#### Scenario: Generate complete report
- **WHEN** GET /api/v1/finance/reconciliation/{accounting_period}
- **THEN** system returns complete report structure
- **AND** all sections are present
- **AND** amounts are rounded to 2 decimal places

#### Scenario: Report with no data returns zeros
- **WHEN** GET /api/v1/finance/reconciliation/{accounting_period} for period with no activity
- **THEN** current_period values are all zero
- **AND** breakdown is empty list
- **AND** unreconciled_records is empty list

### Requirement: Reconciliation status synchronization
The system SHALL support batch updating reconciliation_status based on contract/invoice associations. Status transitions: pending → matched → verified.

#### Scenario: Sync updates matched status
- **WHEN** POST /api/v1/finance/reconciliation/sync with accounting_period
- **THEN** system updates finance_records with contract_id to reconciliation_status='matched'
- **AND** returns updated_count

#### Scenario: Sync atomic on failure
- **WHEN** sync operation fails mid-way
- **THEN** all changes are rolled back
- **AND** no partial updates occur

#### Scenario: Sync with verified invoices
- **WHEN** finance_record is linked to verified invoice
- **THEN** reconciliation_status set to 'verified'

### Requirement: Reconciliation period listing
The system SHALL list all accounting periods that have data (contracts, invoices, or payments).

#### Scenario: List active periods
- **WHEN** GET /api/v1/finance/reconciliation
- **THEN** system returns list of accounting_periods with data
- **AND** ordered by period DESC

#### Scenario: New period appears after activity
- **WHEN** contract is created in 2024-03
- **THEN** GET /api/v1/finance/reconciliation includes '2024-03'

#### Scenario: Empty periods excluded
- **WHEN** no data exists for 2024-06
- **THEN** GET /api/v1/finance/reconciliation does not include '2024-06'

### Requirement: Independent status management
The invoices.status and finance_records.reconciliation_status SHALL be independent. One SHALL NOT drive the other.

#### Scenario: Invoice verified does not change reconciliation status
- **WHEN** invoice status changes to 'verified'
- **THEN** linked finance_records reconciliation_status remains unchanged

#### Scenario: Reconciliation verified does not change invoice status
- **WHEN** reconciliation_sync sets status to 'verified'
- **THEN** linked invoice status remains unchanged

### Requirement: Accounting period calculation from date
The system SHALL calculate accounting_period as YYYY-MM from a given date.

#### Scenario: Calculate period from date
- **WHEN** calculate_accounting_period(date(2024, 1, 15))
- **THEN** returns '2024-01'

#### Scenario: Year boundary
- **WHEN** calculate_accounting_period(date(2024, 12, 31))
- **THEN** returns '2024-12'

#### Scenario: Leap year February
- **WHEN** calculate_accounting_period(date(2024, 2, 29))
- **THEN** returns '2024-02'
