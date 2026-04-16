## ADDED Requirements

### Requirement: Create training experiment
The system SHALL allow creating training experiments associated with a project. `project_id` MUST be provided and reference an existing project.

#### Scenario: Successful experiment creation
- **WHEN** a POST request creates an experiment with valid `project_id`, `name`
- **THEN** the experiment is created with all provided fields including optional `framework`, `hyperparameters`, `metrics`

### Requirement: Link dataset version to experiment
The system SHALL allow linking dataset versions to experiments. Linking SHALL atomically: create the association record in `experiment_dataset_versions`, update the dataset version status to `in_use` if it is currently `ready`. The association MUST be unique — duplicate links SHALL return HTTP 409.

#### Scenario: Link sets dataset version in_use
- **WHEN** a POST request links a ready dataset version to an experiment
- **THEN** the association is created and the dataset version status is atomically updated to `in_use`

#### Scenario: Link archived version rejected
- **WHEN** a POST request attempts to link an archived dataset version
- **THEN** the system returns HTTP 422

#### Scenario: Duplicate link rejected
- **WHEN** a POST request links a dataset version that is already linked to the same experiment
- **THEN** the system returns HTTP 409

### Requirement: Unlink dataset version from experiment
The system SHALL allow unlinking dataset versions from experiments. Unlinking SHALL atomically: remove the association record, check if no other experiment references the version, and if so restore the version status to `ready`.

#### Scenario: Unlink restores ready when no other experiment
- **WHEN** a DELETE request unlinks a version that has no other experiment references
- **THEN** the association is removed and the version status is atomically restored to `ready`

#### Scenario: Unlink keeps in_use when other experiment exists
- **WHEN** a DELETE request unlinks a version that is still referenced by another experiment
- **THEN** the association is removed but the version status remains `in_use`

### Requirement: Experiment freeze rules
When a training experiment has any linked dataset version (exists in `experiment_dataset_versions`), the following fields SHALL NOT be modifiable: `project_id`, `framework`, `hyperparameters`. Other fields (`name`, `description`, `metrics`, `notes`, `started_at`, `finished_at`) SHALL remain modifiable. Attempts to modify frozen fields SHALL return HTTP 409 with error code `EXPERIMENT_FROZEN`.

#### Scenario: Frozen fields rejected after link
- **WHEN** a PUT request attempts to modify `framework` on an experiment with linked dataset versions
- **THEN** the system returns HTTP 409 with error code `EXPERIMENT_FROZEN`

#### Scenario: Mutable fields accepted after link
- **WHEN** a PUT request modifies only `name` on an experiment with linked dataset versions
- **THEN** the update succeeds

### Requirement: Experiment with model versions cannot be deleted
The system SHALL reject deletion of experiments that have associated model versions. The response SHALL indicate the constraint violation.

#### Scenario: Delete experiment with models rejected
- **WHEN** a DELETE request is made for an experiment with associated model versions
- **THEN** the system returns HTTP 409

### Requirement: List experiments by project
The system SHALL return all training experiments for a project, ordered by `created_at` descending.

#### Scenario: Ordered list
- **WHEN** a GET request is made to `/api/v1/projects/{project_id}/training-experiments`
- **THEN** the response contains all experiments sorted by `created_at` descending

### Requirement: Experiment traceability
The system SHALL provide a traceability query returning: the experiment details, linked dataset versions with their datasets, and associated model versions.

#### Scenario: Full traceability
- **WHEN** a GET request is made for experiment traceability
- **THEN** the response includes the experiment, all linked dataset versions (with parent dataset info), and all model versions produced by the experiment
