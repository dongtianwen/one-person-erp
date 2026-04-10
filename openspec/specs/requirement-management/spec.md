## ADDED Requirements

### Requirement: Create requirement version
The system SHALL allow creating a requirement version for a project. The new version's `is_current` SHALL default to `True`. The system SHALL set all other versions of the same project to `is_current = False` within the same transaction. Transaction failure SHALL cause full rollback.

#### Scenario: Successful creation sets as current
- **WHEN** a POST request is made to `/api/v1/projects/{project_id}/requirements` with valid `version_no` and `summary`
- **THEN** a new requirement record is created with `is_current = True`, and all other versions of the same project have `is_current = False`

#### Scenario: No two current versions after creation
- **WHEN** a new requirement version is created for a project that already has a current version
- **THEN** exactly one version has `is_current = True` after the transaction completes

#### Scenario: Transaction rollback on failure
- **WHEN** creating a requirement version fails mid-transaction
- **THEN** no changes are persisted; the original current version remains unchanged

### Requirement: List requirement versions
The system SHALL return all requirement versions for a project, ordered by `created_at` descending.

#### Scenario: Ordered list
- **WHEN** a GET request is made to `/api/v1/projects/{project_id}/requirements`
- **THEN** the response contains all requirement versions sorted by `created_at` descending, each including `id`, `version_no`, `confirm_status`, `is_current`, `created_at`

### Requirement: Get requirement version detail
The system SHALL return the full detail of a requirement version including `summary` and its associated `changes` array.

#### Scenario: Detail with changes
- **WHEN** a GET request is made to `/api/v1/projects/{project_id}/requirements/{requirement_id}`
- **THEN** the response includes the full `summary` and a `changes` array of associated requirement change records

### Requirement: Update requirement version with field restrictions
The system SHALL enforce field modification restrictions based on `confirm_status`. When `confirm_status = confirmed`, `summary` and `version_no` SHALL NOT be modifiable via PUT or PATCH. `confirm_method` and `notes` SHALL be modifiable in any status.

#### Scenario: Update summary in pending status
- **WHEN** a PUT request modifies `summary` on a requirement with `confirm_status = pending`
- **THEN** the update succeeds

#### Scenario: Reject summary update in confirmed status
- **WHEN** a PUT or PATCH request attempts to modify `summary` on a requirement with `confirm_status = confirmed`
- **THEN** the system returns HTTP 422 with message "已确认的需求版本不可修改内容"

#### Scenario: Reject version_no update in confirmed status
- **WHEN** a PUT or PATCH request attempts to modify `version_no` on a requirement with `confirm_status = confirmed`
- **THEN** the system returns HTTP 422 with message "已确认的需求版本不可修改内容"

#### Scenario: Allow notes update in confirmed status
- **WHEN** a PUT or PATCH request modifies `notes` on a requirement with `confirm_status = confirmed`
- **THEN** the update succeeds

### Requirement: Set current requirement version
The system SHALL allow setting a specific version as current. All other versions of the same project SHALL have `is_current` set to `False` in the same transaction.

#### Scenario: Switch current version
- **WHEN** a POST request is made to `/api/v1/projects/{project_id}/requirements/{requirement_id}/set-current`
- **THEN** the specified version becomes the only one with `is_current = True`

#### Scenario: No two current after switch
- **WHEN** a version is set as current
- **THEN** no other version of the same project has `is_current = True`

### Requirement: Create requirement change record
The system SHALL allow creating change records for a requirement version. When `is_billable = True` and `change_order_id` is NULL, the system SHALL reject with HTTP 422.

#### Scenario: Billable change without order rejected
- **WHEN** a POST request creates a change with `is_billable = True` and `change_order_id = NULL`
- **THEN** the system returns HTTP 422 with message "收费变更必须先关联或创建变更单"

#### Scenario: Non-billable change succeeds
- **WHEN** a POST request creates a change with `is_billable = False`
- **THEN** the change record is created successfully

#### Scenario: Billable change with order succeeds
- **WHEN** a POST request creates a change with `is_billable = True` and a valid `change_order_id`
- **THEN** the change record is created successfully

### Requirement: Project not found returns 404
The system SHALL return HTTP 404 for any requirement operation on a non-existent project.

#### Scenario: Non-existent project
- **WHEN** any requirement endpoint is called with a non-existent `project_id`
- **THEN** the system returns HTTP 404
