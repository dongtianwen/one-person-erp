## ADDED Requirements

### Requirement: Create annotation task
The system SHALL allow creating annotation tasks associated with a project and a dataset version. `project_id` and `dataset_version_id` MUST be provided and reference existing records.

#### Scenario: Successful task creation
- **WHEN** a POST request creates a task with valid `project_id`, `dataset_version_id`, `name`
- **THEN** the task is created with `status = pending`

#### Scenario: Non-existent dataset version returns 404
- **WHEN** a POST request creates a task with a non-existent `dataset_version_id`
- **THEN** the system returns HTTP 404

### Requirement: Annotation task status transitions
The system SHALL enforce valid status transitions: pending→in_progress, in_progress→quality_check, quality_check→completed, quality_check→rework, rework→in_progress. The statuses `completed` and `cancelled` are terminal states. Invalid transitions SHALL return HTTP 409.

#### Scenario: Valid transition pending to in_progress
- **WHEN** a PATCH request transitions a task from pending to in_progress
- **THEN** the task status is updated

#### Scenario: Invalid transition returns 409
- **WHEN** a PATCH request attempts to transition from pending directly to completed
- **THEN** the system returns HTTP 409

#### Scenario: Completed is terminal
- **WHEN** a PATCH request attempts to transition from completed to any other status
- **THEN** the system returns HTTP 409

### Requirement: Rework reason mandatory
The system SHALL require `rework_reason` to be non-empty when transitioning a task to rework status. Missing or empty `rework_reason` SHALL return HTTP 422.

#### Scenario: Rework with reason succeeds
- **WHEN** a PATCH request transitions to rework with a non-empty `rework_reason`
- **THEN** the task status is updated to rework and `rework_reason` is stored

#### Scenario: Rework without reason rejected
- **WHEN** a PATCH request transitions to rework with empty or missing `rework_reason`
- **THEN** the system returns HTTP 422

### Requirement: Annotation spec stored in requirements table
The system SHALL store annotation specifications in the `requirements` table with `requirement_type = annotation_spec` and `annotation_task_id` set to the task ID. The annotation tasks table SHALL NOT contain specification content fields.

#### Scenario: Create spec writes to requirements table
- **WHEN** a POST request creates a spec for a task via `/api/v1/annotation-tasks/{task_id}/specs`
- **THEN** a record is created in the requirements table with `requirement_type = annotation_spec` and `annotation_task_id` matching the task

#### Scenario: Spec has correct type and task_id
- **WHEN** a spec is retrieved for a task
- **THEN** the response includes `requirement_type = annotation_spec` and the correct `annotation_task_id`

#### Scenario: Annotation content not in task table
- **WHEN** an annotation task record is retrieved
- **THEN** the response does not contain specification content fields (title, content, etc.)

### Requirement: List annotation tasks by project
The system SHALL return all annotation tasks for a project, ordered by `created_at` descending.

#### Scenario: Ordered list
- **WHEN** a GET request is made to `/api/v1/projects/{project_id}/annotation-tasks`
- **THEN** the response contains all annotation tasks sorted by `created_at` descending

### Requirement: Quality check completion
The system SHALL allow completing quality checks. When passed, the task status transitions to completed. When failed, the task transitions to rework and `rework_reason` is required.

#### Scenario: Quality check passed
- **WHEN** a quality check is completed with `passed = True`
- **THEN** the task status transitions to completed and `quality_check_result` is stored

#### Scenario: Quality check failed requires reason
- **WHEN** a quality check is completed with `passed = False` and `rework_reason` is provided
- **THEN** the task status transitions to rework
