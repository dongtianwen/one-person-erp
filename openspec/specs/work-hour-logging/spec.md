## ADDED Requirements

### Requirement: Create work hour log
The system SHALL allow users to log work hours for a project.

#### Scenario: Create work hour log success
- **WHEN** a user creates a work hour log with valid date, hours_spent, and task_description
- **THEN** the log SHALL be created successfully
- **AND** hours_spent SHALL be > 0 and <= 24
- **AND** log_date, hours_spent, and task_description SHALL be required

#### Scenario: Hours spent must be positive
- **WHEN** a user attempts to create a log with hours_spent <= 0
- **THEN** the system SHALL return HTTP 422
- **AND** the error message SHALL indicate that hours_spent must be greater than 0

#### Scenario: Hours spent exceeds 24 hours rejected
- **WHEN** a user attempts to create a log with hours_spent > 24
- **THEN** the system SHALL return HTTP 422
- **AND** the error message SHALL indicate that hours_spent cannot exceed 24 hours

### Requirement: Work hour summary calculation
The system SHALL calculate work hour summary including deviation rate and threshold status.

#### Scenario: Summary returns correct totals
- **WHEN** a user requests work hour summary for a project
- **THEN** the system SHALL return:
  - estimated_hours: the project's estimated hours (null if not set)
  - actual_hours_total: sum of all logged hours
  - deviation_rate: (actual - estimated) / estimated, or null if estimated_hours = 0
  - deviation_exceeds_threshold: boolean indicating if |deviation_rate| > WORK_HOUR_DEVIATION_THRESHOLD
  - logs: array of work hour logs ordered by log_date DESC

#### Scenario: Deviation rate calculated correctly
- **WHEN** estimated_hours = 100 and actual_hours_total = 130
- **THEN** deviation_rate SHALL be 0.30
- **AND** deviation_exceeds_threshold SHALL be true (assuming threshold = 0.20)

#### Scenario: Deviation rate null when no estimated hours
- **WHEN** a project has estimated_hours = 0 or null
- **THEN** deviation_rate SHALL be null
- **AND** deviation_exceeds_threshold SHALL be false

#### Scenario: Deviation exceeds threshold true when over limit
- **WHEN** |deviation_rate| > WORK_HOUR_DEVIATION_THRESHOLD (0.20)
- **THEN** deviation_exceeds_threshold SHALL be true

#### Scenario: Deviation exceeds threshold false when under limit
- **WHEN** |deviation_rate| <= WORK_HOUR_DEVIATION_THRESHOLD (0.20)
- **THEN** deviation_exceeds_threshold SHALL be false

### Requirement: Deviation note required when exceeds threshold
The system SHALL require a deviation_note when deviation exceeds threshold.

#### Scenario: Deviation note required when over threshold
- **WHEN** a user creates a work hour log that causes deviation_exceeds_threshold = true
- **AND** deviation_note is empty or null
- **THEN** the system SHALL return HTTP 422
- **AND** the error message SHALL indicate that deviation_note is required when exceeding threshold

#### Scenario: Deviation note not required when under threshold
- **WHEN** a user creates a work hour log that causes deviation_exceeds_threshold = false
- **AND** deviation_note is empty or null
- **THEN** the log SHALL be created successfully

### Requirement: Work hour list ordered by date
The system SHALL return work hour logs in descending order by date.

#### Scenario: Work hours list ordered correctly
- **WHEN** a user requests work hour logs for a project
- **THEN** the logs SHALL be ordered by log_date DESC
- **AND** the most recent logs SHALL appear first

### Requirement: Update estimated hours
The system SHALL allow updating the estimated hours for a project.

#### Scenario: Update estimated hours success
- **WHEN** a user updates the estimated_hours for a project
- **THEN** the estimated_hours SHALL be updated
- **AND** the system SHALL return the updated value

#### Scenario: Estimated hours must be non-negative
- **WHEN** a user attempts to set estimated_hours < 0
- **THEN** the system SHALL return HTTP 422
- **AND** the error message SHALL indicate that estimated_hours must be non-negative

### Requirement: Backend is sole source of threshold truth
The system SHALL calculate deviation_exceeds_threshold on the backend using WORK_HOUR_DEVIATION_THRESHOLD constant.

#### Scenario: Frontend consumes backend threshold field
- **WHEN** the frontend receives the work hour summary response
- **THEN** the frontend SHALL use the deviation_exceeds_threshold field from the response
- **AND** the frontend SHALL NOT calculate the threshold independently
- **AND** the frontend SHALL NOT hardcode 20% for threshold comparison

### Requirement: Work hour log fields
The system SHALL store complete work hour log information.

#### Scenario: Work hour log includes all required fields
- **WHEN** a work hour log is created
- **THEN** the log SHALL include:
  - id: auto-increment primary key
  - project_id: foreign key to projects
  - log_date: date of work
  - hours_spent: decimal with 2 precision
  - task_description: text description of work performed
  - deviation_note: text (optional, required when exceeding threshold)
  - created_at: timestamp of log creation
