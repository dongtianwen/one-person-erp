## ADDED Requirements

### Requirement: Invoice fields validation when invoice_no is present
When a finance record has a non-empty `invoice_no`, the system SHALL require `invoice_direction` (enum: output / input), `invoice_type` (enum: general / special / electronic), and `tax_rate` (Decimal). The `tax_amount` SHALL be calculated by the backend using `round(amount * tax_rate, 2)` with Decimal arithmetic; the client SHALL NOT be able to write `tax_amount` directly.

#### Scenario: Create record with invoice_no and all invoice fields
- **WHEN** POST /api/v1/finance/ with invoice_no filled and invoice_direction, invoice_type, tax_rate provided
- **THEN** system creates record with tax_amount calculated by backend, returns HTTP 200

#### Scenario: tax_amount not writable from client
- **WHEN** POST /api/v1/finance/ with invoice_no filled and tax_amount provided in request body
- **THEN** system ignores client-provided tax_amount and calculates it server-side

#### Scenario: tax_amount precision is exactly 2 decimal places
- **WHEN** amount=1000.00 and tax_rate=0.06
- **THEN** tax_amount = 60.00 (round(1000.00 * 0.06, 2))

#### Scenario: invoice_direction required when invoice_no present
- **WHEN** POST /api/v1/finance/ with invoice_no filled but invoice_direction is NULL
- **THEN** system returns HTTP 422 with detail "填写发票号码时必须填写发票方向"

#### Scenario: invoice_type required when invoice_no present
- **WHEN** POST /api/v1/finance/ with invoice_no filled but invoice_type is NULL
- **THEN** system returns HTTP 422 with detail "填写发票号码时必须填写发票类型"

#### Scenario: tax_rate required when invoice_no present
- **WHEN** POST /api/v1/finance/ with invoice_no filled but tax_rate is NULL
- **THEN** system returns HTTP 422 with detail "填写发票号码时必须填写税率"

### Requirement: Invoice fields cleared when invoice_no is empty
When `invoice_no` is NULL or empty string, the system SHALL force invoice_direction, invoice_type, tax_rate, and tax_amount to NULL. This MUST apply to both create (POST) and update (PUT/PATCH) endpoints.

#### Scenario: Create record without invoice_no clears invoice fields
- **WHEN** POST /api/v1/finance/ with invoice_no empty and invoice fields provided
- **THEN** system stores NULL for all four invoice fields

#### Scenario: Update record clearing invoice_no also clears invoice fields
- **WHEN** PUT /api/v1/finance/{id} changes invoice_no from non-empty to empty
- **THEN** system clears invoice_direction, invoice_type, tax_rate, tax_amount to NULL

### Requirement: Quarterly tax summary API
The system SHALL provide `GET /api/v1/finance/tax-summary?year={year}&quarter={quarter}` returning output_tax_total (sum of tax_amount where invoice_direction=output), input_tax_total (sum of tax_amount where invoice_direction=input AND invoice_type=special only), tax_payable (output - input), and record_count. All amounts SHALL be rounded to 2 decimal places. Quarter parameter MUST be 1-4, else HTTP 422.

#### Scenario: Quarterly summary with mixed records
- **WHEN** GET /api/v1/finance/tax-summary?year=2026&quarter=1 with output and input(special) records
- **THEN** response contains correct output_tax_total, input_tax_total, tax_payable, and record_count

#### Scenario: Input tax only includes special invoices
- **WHEN** GET /api/v1/finance/tax-summary includes input records with general and electronic types
- **THEN** only special invoice tax_amount is included in input_tax_total

#### Scenario: Empty quarter returns zeros with HTTP 200
- **WHEN** GET /api/v1/finance/tax-summary for a quarter with no records
- **THEN** response has all totals as 0.00 with HTTP 200

#### Scenario: Invalid quarter returns 422
- **WHEN** GET /api/v1/finance/tax-summary?quarter=5
- **THEN** system returns HTTP 422

#### Scenario: Quarter date range boundary Q1
- **WHEN** get_quarter_date_range(2026, 1) is called
- **THEN** returns (date(2026,1,1), date(2026,3,31))

#### Scenario: Quarter date range boundary Q4
- **WHEN** get_quarter_date_range(2026, 4) is called
- **THEN** returns (date(2026,10,1), date(2026,12,31))
