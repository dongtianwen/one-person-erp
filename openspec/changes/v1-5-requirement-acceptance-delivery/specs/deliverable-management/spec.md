## ADDED Requirements

### Requirement: Create deliverable record
The system SHALL allow creating deliverable records for a project. When `deliverable_type = account_handover`, the request body MAY include an `account_handovers` array.

#### Scenario: Create source code deliverable
- **WHEN** a POST request creates a deliverable with `deliverable_type = source_code`
- **THEN** the deliverable record is created successfully without any handover entries

#### Scenario: Create account handover with valid accounts
- **WHEN** a POST request creates a deliverable with `deliverable_type = account_handover` and `account_handovers` containing entries with valid field names (e.g., `platform_name`, `account_name`)
- **THEN** the deliverable and all handover entries are created in the same transaction

### Requirement: Password field detection in account handovers
The system SHALL reject account handover entries whose JSON field names contain forbidden patterns. Detection SHALL be performed on field names (lowercase substring match), NOT on field values. Forbidden patterns: `password`, `pwd`, `secret`, `passwd`, `token`.

#### Scenario: Reject password field
- **WHEN** a handover entry contains a field named `account_password`
- **THEN** the system returns HTTP 422 with message "账号交接清单禁止存储密码，请仅记录账号名"

#### Scenario: Reject pwd field
- **WHEN** a handover entry contains a field named `user_pwd`
- **THEN** the system returns HTTP 422

#### Scenario: Reject token field
- **WHEN** a handover entry contains a field named `access_token`
- **THEN** the system returns HTTP 422

#### Scenario: Allow notes field
- **WHEN** a handover entry contains a field named `notes` (even if the value contains password-like content)
- **THEN** the entry is accepted; detection only checks field names

#### Scenario: Detection checks field names not values
- **WHEN** a handover entry has field `notes` with value "密码已通过微信发送"
- **THEN** the entry is accepted because `notes` is not a forbidden field name

### Requirement: Account handovers in same transaction
The `account_handovers` array and the main deliverable record SHALL be written in the same transaction.

#### Scenario: Transaction atomicity
- **WHEN** a handover entry creation fails after the deliverable is created
- **THEN** both the deliverable and all handover entries are rolled back

### Requirement: List deliverables
The system SHALL return all deliverables for a project, ordered by `delivery_date` descending. The list SHALL support filtering by `deliverable_type`.

#### Scenario: Ordered list
- **WHEN** a GET request is made to `/api/v1/projects/{project_id}/deliverables`
- **THEN** the response contains all deliverables sorted by `delivery_date` descending

#### Scenario: Filter by type
- **WHEN** a GET request includes `deliverable_type=source_code` query parameter
- **THEN** only deliverables matching that type are returned

### Requirement: Get deliverable detail with handovers
The system SHALL return the deliverable detail. When the type is `account_handover`, the response SHALL include the `account_handovers` array.

#### Scenario: Detail includes handovers
- **WHEN** a GET request is made for an `account_handover` type deliverable
- **THEN** the response includes the `account_handovers` array with all entries

### Requirement: Deliverable delete returns 405
The system SHALL return HTTP 405 for any DELETE request on deliverable records.

#### Scenario: Delete rejection
- **WHEN** a DELETE request is made to `/api/v1/projects/{project_id}/deliverables/{deliverable_id}`
- **THEN** the system returns HTTP 405

### Requirement: Password detection function independent
The `contains_password_field()` function SHALL be independently callable without starting the FastAPI application.

#### Scenario: Independent function test
- **WHEN** the function is imported and called with various dict inputs
- **THEN** it correctly identifies forbidden field name patterns

### Requirement: Project not found returns 404
The system SHALL return HTTP 404 for deliverable operations on a non-existent project.

#### Scenario: Non-existent project
- **WHEN** any deliverable endpoint is called with a non-existent `project_id`
- **THEN** the system returns HTTP 404
