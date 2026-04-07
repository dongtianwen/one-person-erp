## ADDED Requirements

### Requirement: Create change order with auto-generated number
The system SHALL allow creating change orders for a contract. The `order_no` SHALL be auto-generated in the format `BG-YYYYMMDD-NNN` where NNN is a 3-digit zero-padded sequence number (daily count + 1). Generation SHALL occur within the creation transaction to prevent concurrent duplicates.

#### Scenario: Auto-generated order number
- **WHEN** a POST request creates a change order for a contract
- **THEN** the response includes an `order_no` in the format `BG-YYYYMMDD-001` for the first order of the day

#### Scenario: Number format correct
- **WHEN** a change order is created
- **THEN** `order_no` matches the pattern `BG-YYYYMMDD-NNN` with 3-digit zero-padded sequence

#### Scenario: Sequence increments same day
- **WHEN** multiple change orders are created on the same day
- **THEN** each subsequent order gets an incremented sequence number (001, 002, 003...)

#### Scenario: Unique order number
- **WHEN** the `generate_change_order_no()` function is called
- **THEN** it returns a unique number that does not duplicate any existing order_no

### Requirement: List change orders with totals
The system SHALL return all change orders for a contract, ordered by `created_at` descending. The response SHALL include `confirmed_total` and `actual_receivable` as additional fields.

#### Scenario: List includes totals
- **WHEN** a GET request is made to `/api/v1/contracts/{contract_id}/change-orders`
- **THEN** the response includes `confirmed_total` (sum of confirmed/in_progress/completed orders) and `actual_receivable` (contract amount + confirmed_total)

### Requirement: Actual receivable calculation
The `confirmed_total` SHALL be the sum of `amount` for change orders with `status IN (confirmed, in_progress, completed)`, rounded to 2 decimal places. The `actual_receivable` SHALL be `round(contract.amount + confirmed_total, 2)`. Draft and sent orders SHALL NOT be included.

#### Scenario: Includes confirmed status
- **WHEN** calculating `confirmed_total` and a change order has `status = confirmed`
- **THEN** its amount is included

#### Scenario: Includes in_progress status
- **WHEN** calculating `confirmed_total` and a change order has `status = in_progress`
- **THEN** its amount is included

#### Scenario: Includes completed status
- **WHEN** calculating `confirmed_total` and a change order has `status = completed`
- **THEN** its amount is included

#### Scenario: Excludes draft status
- **WHEN** calculating `confirmed_total` and a change order has `status = draft`
- **THEN** its amount is NOT included

#### Scenario: Excludes sent status
- **WHEN** calculating `confirmed_total` and a change order has `status = sent`
- **THEN** its amount is NOT included

### Requirement: Status transition validation
The system SHALL validate status transitions against `CHANGE_ORDER_VALID_TRANSITIONS`. Illegal transitions SHALL return HTTP 422.

#### Scenario: Draft to sent allowed
- **WHEN** a change order transitions from `draft` to `sent`
- **THEN** the transition succeeds

#### Scenario: Draft to confirmed allowed (skip sent)
- **WHEN** a change order transitions from `draft` to `confirmed`
- **THEN** the transition succeeds

#### Scenario: Draft to completed allowed (early termination)
- **WHEN** a change order transitions from `draft` to `completed`
- **THEN** the transition succeeds

#### Scenario: Completed to any rejected
- **WHEN** a change order with `status = completed` attempts any transition
- **THEN** the system returns HTTP 422

#### Scenario: Illegal transition returns 422 with message
- **WHEN** an illegal transition is attempted (e.g., `completed` to `draft`)
- **THEN** the system returns HTTP 422 with message "状态从 {current_status} 变更为 {target_status} 不被允许"

### Requirement: Change order field modification restrictions
When `status` is `confirmed`, `in_progress`, or `completed`, the `amount` and `description` fields SHALL NOT be modifiable via PUT or PATCH.

#### Scenario: Update draft amount succeeds
- **WHEN** a PUT request modifies `amount` on a change order with `status = draft`
- **THEN** the update succeeds

#### Scenario: Reject confirmed amount update
- **WHEN** a PUT or PATCH request attempts to modify `amount` on a change order with `status = confirmed`
- **THEN** the system returns HTTP 422 with message "已确认的变更单不可修改金额和描述"

#### Scenario: Reject confirmed description update
- **WHEN** a PUT or PATCH request attempts to modify `description` on a change order with `status = confirmed`
- **THEN** the system returns HTTP 422 with message "已确认的变更单不可修改金额和描述"

### Requirement: Project change order summary (read-only)
The system SHALL provide a read-only summary endpoint for change orders at the project level, showing only `order_no`, `title`, `amount`, `status`, `contract_id`, `contract_no`. No write operations SHALL be available.

#### Scenario: Summary is read-only
- **WHEN** a GET request is made to `/api/v1/projects/{project_id}/change-orders/summary`
- **THEN** the response contains change order summaries from all related contracts, with no write operation endpoints available

### Requirement: Independent utility functions
The `generate_change_order_no()`, `validate_status_transition()`, and `calculate_actual_receivable()` functions SHALL be independently callable without starting the FastAPI application.

#### Scenario: Validate transition function
- **WHEN** `validate_status_transition()` is called with various status pairs
- **THEN** it returns True for valid transitions and False for invalid ones

#### Scenario: Generate order number function
- **WHEN** `generate_change_order_no()` is called
- **THEN** it returns a correctly formatted unique order number
