## ADDED Requirements

### Requirement: Create maintenance period
The system SHALL allow creating maintenance/service period records for a project. `end_date` before `start_date` SHALL be rejected.

#### Scenario: Successful creation
- **WHEN** a POST request creates a maintenance period with valid dates and fields
- **THEN** the record is created with `status = active`

#### Scenario: End before start rejected
- **WHEN** a POST request creates a maintenance period with `end_date < start_date`
- **THEN** the system returns HTTP 422 with message "结束日期不得早于开始日期"

### Requirement: Near-expiry reminder on creation
When a maintenance period is created with `end_date` within `MAINTENANCE_REMINDER_DAYS_BEFORE` days from today, the system SHALL create an expiry reminder. The reminder creation SHALL be idempotent (no duplicate reminders).

#### Scenario: Near-expiry generates reminder
- **WHEN** a maintenance period is created with `end_date` within 30 days from today
- **THEN** a reminder is created for the maintenance period expiry

#### Scenario: Far-expiry no immediate reminder
- **WHEN** a maintenance period is created with `end_date` more than 30 days from today
- **THEN** no reminder is created immediately

#### Scenario: Reminder idempotent
- **WHEN** a reminder already exists for a maintenance period
- **THEN** no duplicate reminder is created

### Requirement: List maintenance periods
The system SHALL return all maintenance periods for a project, ordered by `end_date` ascending. The list SHALL support filtering by `status`.

#### Scenario: Ordered list
- **WHEN** a GET request is made to `/api/v1/projects/{project_id}/maintenance-periods`
- **THEN** the response contains all maintenance periods sorted by `end_date` ascending

#### Scenario: Filter by status
- **WHEN** a GET request includes `status=active` query parameter
- **THEN** only active maintenance periods are returned

### Requirement: Renew maintenance period
The system SHALL allow renewing an active maintenance period. The renewal operation MUST be atomic within a single transaction: (1) create new record with `start_date = original.end_date + 1 day`, (2) set original `status = renewed`, (3) set original `renewed_by_id = new record ID`.

#### Scenario: New start date is end plus one
- **WHEN** a renewal is performed
- **THEN** the new record's `start_date` equals the original record's `end_date + 1 day`

#### Scenario: Explicit end date required
- **WHEN** a renewal request does not include `end_date`
- **THEN** the system returns HTTP 422 (end_date is mandatory)

#### Scenario: End date before start rejected
- **WHEN** a renewal request provides `end_date` before the auto-calculated `start_date`
- **THEN** the system returns HTTP 422

#### Scenario: Original status becomes renewed
- **WHEN** a renewal completes successfully
- **THEN** the original record's `status = renewed`

#### Scenario: Original renewed_by_id set
- **WHEN** a renewal completes successfully
- **THEN** the original record's `renewed_by_id` equals the new record's ID

#### Scenario: Annual fee appended to reminder notes
- **WHEN** a renewal has `annual_fee > 0`
- **THEN** the reminder notes include "年费金额：¥{annual_fee}，请确认是否续签"

#### Scenario: Renewal transaction atomic
- **WHEN** any step in the renewal fails
- **THEN** all changes are rolled back; the original record remains unchanged

### Requirement: Partial update maintenance period
The system SHALL allow PATCH updates only to `service_description`, `annual_fee`, and `notes` fields. When `status` is `expired`, `renewed`, or `terminated`, updates SHALL be rejected.

#### Scenario: Active period allowed fields
- **WHEN** a PATCH request updates `service_description`, `annual_fee`, or `notes` on an active period
- **THEN** the update succeeds

#### Scenario: Expired period rejected
- **WHEN** a PATCH request is made on a period with `status = expired`
- **THEN** the system returns HTTP 422 with message "已结束的服务期不可修改"

#### Scenario: Disallowed fields rejected
- **WHEN** a PATCH request attempts to modify fields other than `service_description`, `annual_fee`, or `notes`
- **THEN** the system returns HTTP 422 with message "仅允许修改服务说明、年费和备注"

### Requirement: Event-driven expiry check for maintenance
The event-driven check function SHALL be extended to: (1) set `status = expired` for active periods past their `end_date`, (2) create expiry reminders for active periods within `MAINTENANCE_REMINDER_DAYS_BEFORE` days of expiry (idempotent).

#### Scenario: Expire overdue maintenance
- **WHEN** the event-driven check runs and a maintenance period has `status = active` and `end_date < today`
- **THEN** the period's `status` is updated to `expired`

#### Scenario: Create reminder near expiry
- **WHEN** the event-driven check runs and a maintenance period has `end_date` within 30 days
- **THEN** a reminder is created if one does not already exist

#### Scenario: Event-driven reminder idempotent
- **WHEN** the event-driven check runs multiple times for the same period
- **THEN** only one reminder is created

### Requirement: Dashboard active maintenance count
The dashboard endpoint SHALL include `active_maintenance_count` in its response.

#### Scenario: Dashboard includes count
- **WHEN** the dashboard endpoint is called
- **THEN** the response includes `active_maintenance_count` with the count of active maintenance periods
