## MODIFIED Requirements

### Requirement: Event-driven overdue checks
The system SHALL perform comprehensive overdue checks when triggered by user actions (login, page load). Checks SHALL cover: reminder status escalation (v1.1), quotation expiry and customer asset expiry (v1.2), and maintenance period expiry and near-expiry reminders (v1.5).

#### Scenario: Maintenance period expires when overdue
- **WHEN** the event-driven check runs and a maintenance period has `status = active` and `end_date < today`
- **THEN** the period's `status` is updated to `expired`

#### Scenario: Maintenance period near-expiry reminder created
- **WHEN** the event-driven check runs and a maintenance period has `status = active` and `end_date` is within `MAINTENANCE_REMINDER_DAYS_BEFORE` days from today and no reminder exists
- **THEN** a new reminder is created for that maintenance period

#### Scenario: Maintenance reminder idempotent
- **WHEN** the event-driven check runs and a reminder already exists for a maintenance period
- **THEN** no duplicate reminder is created
