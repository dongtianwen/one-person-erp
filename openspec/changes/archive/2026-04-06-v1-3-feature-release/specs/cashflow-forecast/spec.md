## ADDED Requirements

### Requirement: 90-day forecast with weekly grouping
The system SHALL provide `GET /api/v1/cashflow/forecast` returning a list of weekly predictions for the next 90 days from today. Weeks SHALL be natural weeks (Monday start). Only contracts with status in `["active", "executing"]` SHALL be included. Contracts with NULL expected_payment_date or receivable <= 0 SHALL be skipped silently.

#### Scenario: Forecast returns correct week count
- **WHEN** GET /api/v1/cashflow/forecast
- **THEN** response contains weeks covering exactly 90 consecutive days from start_date

#### Scenario: First week starts on Monday
- **WHEN** the forecast weeks are generated
- **THEN** each week_start is a Monday (weekday() == 0)

#### Scenario: Last day is exactly day 90
- **WHEN** start_date is 2026-04-06
- **THEN** the last day in the forecast range is 2026-07-04

#### Scenario: Active contract included in forecast
- **WHEN** a contract with status="active" and expected_payment_date within 90 days exists
- **THEN** its receivable amount is allocated to the corresponding week

#### Scenario: Executing contract included in forecast
- **WHEN** a contract with status="executing" and expected_payment_date within 90 days exists
- **THEN** its receivable amount is allocated to the corresponding week

#### Scenario: Completed contract excluded
- **WHEN** a contract with status="completed" exists
- **THEN** it is NOT included in the forecast

#### Scenario: Draft contract excluded
- **WHEN** a contract with status="draft" exists
- **THEN** it is NOT included in the forecast

#### Scenario: NULL payment date skipped without error
- **WHEN** an active contract has NULL expected_payment_date
- **THEN** it is silently skipped, no error raised

#### Scenario: Receivable equals contract amount minus confirmed income
- **WHEN** contract amount=50000 and confirmed income=20000 for that contract
- **THEN** receivable = 30000.00 allocated to the corresponding week

#### Scenario: Only confirmed income of same contract counted
- **WHEN** contract A has confirmed income from records NOT related to contract A
- **THEN** those records are NOT counted as contract A's confirmed income

### Requirement: Weekly expense from historical average
Expense prediction SHALL be based on confirmed expenses in the last 3 complete calendar months (excluding current month). Monthly average = total / 3, weekly average = round(monthly / 4.33, 2). Same weekly amount allocated to each week. No history = 0.00.

#### Scenario: Expense from last 3 complete months only
- **WHEN** today is 2026-04-06 and confirmed expenses exist in Jan-Mar 2026
- **THEN** expense calculation uses only records from 2026-01-01 to 2026-03-31

#### Scenario: Zero expense when no history
- **WHEN** no confirmed expense records exist in the last 3 months
- **THEN** weekly predicted_expense = 0.00 for all weeks, no error

#### Scenario: No data returns all zeros with HTTP 200
- **WHEN** no contracts and no expense history exist
- **THEN** forecast returns weeks with all amounts as 0.00, HTTP 200

### Requirement: Forecast response structure
Response SHALL contain `forecast` array (week_index, week_start, week_end, predicted_income, predicted_expense, predicted_net) and `summary` object (total_predicted_income, total_predicted_expense, total_predicted_net). All amounts MUST be rounded to 2 decimal places. Summary totals MUST equal sum of weekly values.

#### Scenario: Response structure exact match
- **WHEN** GET /api/v1/cashflow/forecast returns data
- **THEN** response contains exactly forecast array and summary object with specified fields

#### Scenario: All amounts two decimal precision
- **WHEN** forecast response is generated
- **THEN** all numeric fields have exactly 2 decimal places

#### Scenario: Summary totals match weekly sum
- **WHEN** forecast has multiple weeks
- **THEN** summary totals equal the sum of corresponding weekly values
