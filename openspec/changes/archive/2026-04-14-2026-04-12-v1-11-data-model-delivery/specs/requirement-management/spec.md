## MODIFIED Requirements

### Requirement: Create requirement version
The system SHALL allow creating a requirement version for a project. The new version's `is_current` SHALL default to `True`. The system SHALL set all other versions of the same project to `is_current = False` within the same transaction. Transaction failure SHALL cause full rollback. When `requirement_type = annotation_spec`, the `annotation_task_id` field MAY be provided to associate the requirement with an annotation task.

#### Scenario: Successful creation sets as current
- **WHEN** a POST request is made to `/api/v1/projects/{project_id}/requirements` with valid `version_no` and `summary`
- **THEN** a new requirement record is created with `is_current = True`, and all other versions of the same project have `is_current = False`

#### Scenario: No two current versions after creation
- **WHEN** a new requirement version is created for a project that already has a current version
- **THEN** exactly one version has `is_current = True` after the transaction completes

#### Scenario: Transaction rollback on failure
- **WHEN** creating a requirement version fails mid-transaction
- **THEN** no changes are persisted; the original current version remains unchanged

## ADDED Requirements

### Requirement: Annotation spec requirement type
The system SHALL support `requirement_type = annotation_spec` for requirements that serve as annotation specifications. Such requirements MAY have `annotation_task_id` set to associate them with a specific annotation task.

#### Scenario: Create annotation spec requirement
- **WHEN** a POST request creates a requirement with `requirement_type = annotation_spec` and a valid `annotation_task_id`
- **THEN** the requirement is created with the annotation task association

#### Scenario: List specs by annotation task
- **WHEN** a GET request is made to `/api/v1/annotation-tasks/{task_id}/specs`
- **THEN** the response contains all requirements with `requirement_type = annotation_spec` and the matching `annotation_task_id`

#### Scenario: Requirement detail includes task reference
- **WHEN** a GET request retrieves a requirement with `annotation_task_id`
- **THEN** the response includes the `annotation_task_id` field
