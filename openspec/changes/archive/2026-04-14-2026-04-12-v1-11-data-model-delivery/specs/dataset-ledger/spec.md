## ADDED Requirements

### Requirement: Create dataset
The system SHALL allow creating datasets associated with a project. `project_id` MUST be provided and reference an existing project. `dataset_type` SHALL be validated against the whitelist: image, text, audio, video, multimodal, other.

#### Scenario: Successful dataset creation
- **WHEN** a POST request creates a dataset with valid `project_id`, `name`, and `dataset_type`
- **THEN** the dataset record is created and returned with `id`, `created_at`, `updated_at`

#### Scenario: Invalid dataset type rejected
- **WHEN** a POST request creates a dataset with `dataset_type = "invalid_type"`
- **THEN** the system returns HTTP 422

#### Scenario: Non-existent project returns 404
- **WHEN** a POST request creates a dataset with a non-existent `project_id`
- **THEN** the system returns HTTP 404

### Requirement: List datasets by project
The system SHALL return all datasets for a project, ordered by `created_at` descending.

#### Scenario: Ordered list
- **WHEN** a GET request is made to `/api/v1/projects/{project_id}/datasets`
- **THEN** the response contains all datasets sorted by `created_at` descending

### Requirement: Create dataset version
The system SHALL allow creating dataset versions. `version_no` MUST match pattern `^v\d+\.\d+$` and MUST be unique within the same dataset. New versions default to `status = draft`. The system SHALL accept `data_source`, `label_schema_version`, and `change_summary` as optional metadata fields.

#### Scenario: Successful version creation with metadata
- **WHEN** a POST request creates a version with valid `version_no`, `sample_count`, `file_path`, `data_source`, `label_schema_version`
- **THEN** the version is created with `status = draft` and all metadata fields stored

#### Scenario: Version number format validated
- **WHEN** a POST request creates a version with `version_no = "1.0"` (missing v prefix)
- **THEN** the system returns HTTP 422

#### Scenario: Duplicate version number rejected
- **WHEN** a POST request creates a version with a `version_no` that already exists for the same dataset
- **THEN** the system returns HTTP 409

### Requirement: Dataset version freeze rules
The system SHALL enforce freeze rules when `status` is in (ready, in_use, archived). The following fields SHALL NOT be modifiable: version_no, dataset_id, sample_count, file_path, data_source, label_schema_version. The fields `notes` and `change_summary` SHALL remain modifiable in any status. Attempts to modify frozen fields SHALL return HTTP 409 with error code `DATASET_VERSION_FROZEN`.

#### Scenario: Frozen fields rejected when ready
- **WHEN** a PUT request attempts to modify `sample_count` on a version with `status = ready`
- **THEN** the system returns HTTP 409 with error code `DATASET_VERSION_FROZEN`

#### Scenario: Frozen fields rejected when in_use
- **WHEN** a PUT request attempts to modify `file_path` on a version with `status = in_use`
- **THEN** the system returns HTTP 409 with error code `DATASET_VERSION_FROZEN`

#### Scenario: Notes mutable when frozen
- **WHEN** a PUT request modifies only `notes` on a version with `status = ready`
- **THEN** the update succeeds

#### Scenario: Change summary mutable when frozen
- **WHEN** a PUT request modifies only `change_summary` on a version with `status = in_use`
- **THEN** the update succeeds

### Requirement: in_use status system-only
The `in_use` status SHALL only be set by the system when a dataset version is linked to a training experiment. API requests that directly set `status = in_use` SHALL be rejected with HTTP 422.

#### Scenario: API reject in_use status
- **WHEN** a POST or PUT request includes `status = in_use` in the request body
- **THEN** the system returns HTTP 422

### Requirement: in_use version cannot be deleted
The system SHALL reject deletion of dataset versions with `status = in_use`. The response SHALL return HTTP 409 with error code `VERSION_IN_USE_CANNOT_DELETE`.

#### Scenario: Delete in_use version rejected
- **WHEN** a DELETE request is made for a version with `status = in_use`
- **THEN** the system returns HTTP 409 with error code `VERSION_IN_USE_CANNOT_DELETE`

### Requirement: Dataset version state transitions
The system SHALL support transitioning dataset versions: draft→ready (via PATCH /ready), ready→archived (via PATCH /archive). The `in_use` status is system-managed only.

#### Scenario: Ready transition success
- **WHEN** a PATCH request transitions a draft version to ready
- **THEN** the version status is updated to ready and frozen fields become protected

#### Scenario: Archive transition success
- **WHEN** a PATCH request transitions a ready version to archived
- **THEN** the version status is updated to archived

### Requirement: Dataset not found returns 404
The system SHALL return HTTP 404 for operations on non-existent datasets or dataset versions.

#### Scenario: Dataset not found
- **WHEN** any dataset endpoint is called with a non-existent `dataset_id`
- **THEN** the system returns HTTP 404

#### Scenario: Version not found
- **WHEN** any version endpoint is called with a non-existent `version_id`
- **THEN** the system returns HTTP 404

### Requirement: Project dataset summary
The system SHALL provide a summary endpoint returning dataset count, version count by status, for a given project.

#### Scenario: Summary returns counts
- **WHEN** a GET request is made to `/api/v1/projects/{project_id}/datasets/summary`
- **THEN** the response includes total dataset count and version counts grouped by status
