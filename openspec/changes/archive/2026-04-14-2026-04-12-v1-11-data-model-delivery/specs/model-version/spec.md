## ADDED Requirements

### Requirement: Create model version
The system SHALL allow creating model versions associated with a project and experiment. `experiment_id` MUST be provided and reference an existing training experiment. `version_no` MUST match pattern `^v\d+\.\d+\.\d+$` and MUST be unique within the same project and name combination. New versions default to `status = training`.

#### Scenario: Successful model version creation
- **WHEN** a POST request creates a model version with valid `project_id`, `experiment_id`, `name`, `version_no`
- **THEN** the model version is created with `status = training`

#### Scenario: Version number format validated
- **WHEN** a POST request creates a model version with `version_no = "v1.0"` (two segments instead of three)
- **THEN** the system returns HTTP 422

#### Scenario: Duplicate version rejected
- **WHEN** a POST request creates a model version with the same `project_id`, `name`, `version_no` as an existing record
- **THEN** the system returns HTTP 409

### Requirement: Model version freeze rules
When `status` is in (ready, delivered, deprecated), the following fields SHALL NOT be modifiable: version_no, experiment_id, name, file_path, metrics. The field `notes` SHALL remain modifiable in any status. Attempts to modify frozen fields SHALL return HTTP 409 with error code `MODEL_VERSION_FROZEN`.

#### Scenario: Frozen fields rejected when ready
- **WHEN** a PUT request attempts to modify `metrics` on a model version with `status = ready`
- **THEN** the system returns HTTP 409 with error code `MODEL_VERSION_FROZEN`

#### Scenario: Notes mutable when frozen
- **WHEN** a PUT request modifies only `notes` on a model version with `status = delivered`
- **THEN** the update succeeds

### Requirement: Model version state transitions
The system SHALL support transitioning model versions: training→ready (via PATCH /ready), ready→deprecated (via PATCH /deprecate). The `delivered` status is set by the delivery package system.

#### Scenario: Ready transition success
- **WHEN** a PATCH request transitions a training model version to ready
- **THEN** the status is updated and frozen fields become protected

#### Scenario: Deprecate transition success
- **WHEN** a PATCH request transitions a ready model version to deprecated
- **THEN** the status is updated to deprecated

### Requirement: Delivered model version cannot be deleted
The system SHALL reject deletion of model versions with `status = delivered`. The response SHALL return HTTP 409 with error code `DELIVERED_MODEL_CANNOT_DELETE`.

#### Scenario: Delete delivered model rejected
- **WHEN** a DELETE request is made for a model version with `status = delivered`
- **THEN** the system returns HTTP 409 with error code `DELIVERED_MODEL_CANNOT_DELETE`

### Requirement: List model versions
The system SHALL return model versions filtered by project or by experiment, ordered by `created_at` descending.

#### Scenario: List by project
- **WHEN** a GET request is made to `/api/v1/projects/{project_id}/model-versions`
- **THEN** the response contains all model versions for the project

#### Scenario: List by experiment
- **WHEN** a GET request is made to `/api/v1/training-experiments/{experiment_id}/model-versions`
- **THEN** the response contains all model versions produced by the experiment

### Requirement: Model version traceability
The system SHALL provide a traceability query returning: the model version, its parent experiment, and the dataset versions linked to that experiment.

#### Scenario: Full traceability
- **WHEN** a GET request is made for model version traceability
- **THEN** the response includes the model version, the experiment that produced it, and all dataset versions used in that experiment
