## ADDED Requirements

### Requirement: Create acceptance record with reminder trigger
The system SHALL allow creating acceptance records. When `result` is `passed` or `conditional` AND `trigger_payment_reminder = True`, the system SHALL create a payment reminder in the `reminders` table within the same transaction. The `reminder_id` SHALL be written back to the acceptance record.

#### Scenario: Passed acceptance triggers reminder
- **WHEN** a POST request creates an acceptance with `result = passed` and `trigger_payment_reminder = True`
- **THEN** a reminder is created with `title = "收款提醒：{acceptance_name}"`, `type = custom`, `is_critical = False`, `status = pending`, and the `reminder_id` is written back to the acceptance record

#### Scenario: Conditional acceptance triggers reminder
- **WHEN** a POST request creates an acceptance with `result = conditional` and `trigger_payment_reminder = True`
- **THEN** a reminder is created and `reminder_id` written back

#### Scenario: Failed acceptance no reminder
- **WHEN** a POST request creates an acceptance with `result = failed`
- **THEN** no reminder is created, `reminder_id` remains NULL

#### Scenario: Reminder in same transaction
- **WHEN** the reminder creation fails after the acceptance record is created
- **THEN** both the acceptance and reminder are rolled back

#### Scenario: Reminder ID written back
- **WHEN** a reminder is created for an acceptance
- **THEN** the acceptance record's `reminder_id` field matches the created reminder's ID

### Requirement: List acceptance records
The system SHALL return all acceptance records for a project, ordered by `acceptance_date` descending.

#### Scenario: Ordered list
- **WHEN** a GET request is made to `/api/v1/projects/{project_id}/acceptances`
- **THEN** the response contains all acceptance records sorted by `acceptance_date` descending

### Requirement: Acceptance delete returns 405
The system SHALL return HTTP 405 for any DELETE request on acceptance records. No deletion SHALL be performed.

#### Scenario: Delete rejection
- **WHEN** a DELETE request is made to `/api/v1/projects/{project_id}/acceptances/{acceptance_id}`
- **THEN** the system returns HTTP 405 without performing any operation

### Requirement: Acceptance result immutable
The `result` field SHALL NOT be modifiable after creation via PUT or PATCH. Attempting to modify `result` SHALL return HTTP 422.

#### Scenario: PUT result rejected
- **WHEN** a PUT request attempts to modify the `result` field
- **THEN** the system returns HTTP 422 with message "验收结果不可修改"

#### Scenario: PATCH result rejected
- **WHEN** a PATCH request attempts to modify the `result` field
- **THEN** the system returns HTTP 422 with message "验收结果不可修改"

### Requirement: Append notes to acceptance
The system SHALL allow appending notes to an acceptance record. The format SHALL be `existing_content + NOTES_SEPARATOR + new_note`. When existing content is empty, the new note SHALL be stored directly without a separator.

#### Scenario: Append with separator
- **WHEN** a PATCH request is made to `/api/v1/projects/{project_id}/acceptances/{acceptance_id}/append-notes` with new note content and existing notes are non-empty
- **THEN** the new content is appended with a newline separator

#### Scenario: Append to empty notes
- **WHEN** a PATCH request appends notes to an acceptance with empty or NULL notes
- **THEN** the new note is stored directly without a separator

### Requirement: Acceptance detail response structure
The system SHALL return the complete acceptance record with all fields in the detail response.

#### Scenario: Complete detail
- **WHEN** a GET request is made to `/api/v1/projects/{project_id}/acceptances/{acceptance_id}`
- **THEN** the response includes all acceptance fields including `acceptance_name`, `acceptance_date`, `acceptor_name`, `acceptor_title`, `result`, `notes`, `trigger_payment_reminder`, `reminder_id`, `confirm_method`

### Requirement: Project not found returns 404
The system SHALL return HTTP 404 for acceptance operations on a non-existent project.

#### Scenario: Non-existent project
- **WHEN** any acceptance endpoint is called with a non-existent `project_id`
- **THEN** the system returns HTTP 404
