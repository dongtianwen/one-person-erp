## ADDED Requirements

### Requirement: Create delivery package
The system SHALL allow creating delivery packages associated with a project. `project_id` MUST be provided. New packages default to `status = draft`.

#### Scenario: Successful package creation
- **WHEN** a POST request creates a package with valid `project_id` and `name`
- **THEN** the package is created with `status = draft`

### Requirement: Associate model versions with package
The system SHALL allow associating model versions with a delivery package. Associations MUST be unique — duplicates SHALL return HTTP 409.

#### Scenario: Successful model association
- **WHEN** a POST request associates a model version with a package
- **THEN** the association is created in `package_model_versions`

#### Scenario: Duplicate association rejected
- **WHEN** a POST request associates a model version already in the package
- **THEN** the system returns HTTP 409

### Requirement: Associate dataset versions with package
The system SHALL allow associating dataset versions with a delivery package. Associations MUST be unique.

#### Scenario: Successful dataset association
- **WHEN** a POST request associates a dataset version with a package
- **THEN** the association is created in `package_dataset_versions`

### Requirement: Ready requires content
The system SHALL reject transitioning a package to `ready` if no model versions or dataset versions are associated. The response SHALL return HTTP 422.

#### Scenario: Ready with content succeeds
- **WHEN** a PATCH request transitions a package with at least one associated version to ready
- **THEN** the package status is updated to ready

#### Scenario: Ready without content rejected
- **WHEN** a PATCH request transitions an empty package to ready
- **THEN** the system returns HTTP 422

### Requirement: Deliver package atomically
The system SHALL atomically execute the deliver operation: set `delivery_packages.status = delivered`, set `delivered_at` to current timestamp, and update all associated model versions' status to `delivered`. The entire operation MUST be a single transaction — partial updates SHALL be rolled back.

#### Scenario: Deliver updates model versions
- **WHEN** a PATCH request delivers a ready package
- **THEN** the package status becomes delivered, `delivered_at` is set, and all associated model versions status becomes delivered

#### Scenario: Deliver is atomic
- **WHEN** a model version status update fails during deliver
- **THEN** the entire transaction is rolled back — no status changes are persisted

### Requirement: Create package acceptance
The system SHALL allow creating acceptance records for a delivery package. `delivery_package_id` MUST be provided and MUST match the current package. The `acceptance_type` SHALL be auto-determined based on package content: if model versions exist, type is `model`; if only dataset versions exist, type is `dataset`. When `result = passed`, the system SHALL atomically update the package status to `accepted`. Only one acceptance record SHALL be allowed per package.

#### Scenario: Acceptance requires delivery package id
- **WHEN** a POST request creates an acceptance without `delivery_package_id`
- **THEN** the system returns HTTP 422

#### Scenario: Acceptance package id matches current
- **WHEN** a POST request creates an acceptance with a `delivery_package_id` that does not match the current package
- **THEN** the system returns HTTP 422

#### Scenario: Acceptance type auto determined as model
- **WHEN** a POST request creates an acceptance for a package containing model versions
- **THEN** the `acceptance_type` is set to `model`

#### Scenario: Acceptance type auto determined as dataset
- **WHEN** a POST request creates an acceptance for a package containing only dataset versions
- **THEN** the `acceptance_type` is set to `dataset`

#### Scenario: Acceptance passed transitions package accepted
- **WHEN** a POST request creates an acceptance with `result = passed`
- **THEN** the acceptance is created and the package status is atomically updated to `accepted`

#### Scenario: Package only one acceptance
- **WHEN** a POST request creates a second acceptance for a package that already has one
- **THEN** the system returns HTTP 409

### Requirement: Accepted package cannot be deleted
The system SHALL reject deletion of packages with `status = accepted`. The response SHALL return HTTP 409 with error code `ACCEPTED_PACKAGE_CANNOT_DELETE`.

#### Scenario: Delete accepted package rejected
- **WHEN** a DELETE request is made for a package with `status = accepted`
- **THEN** the system returns HTTP 409 with error code `ACCEPTED_PACKAGE_CANNOT_DELETE`

### Requirement: Package traceability
The system SHALL provide a traceability query returning: the package details, associated model versions with their experiments and dataset versions, associated dataset versions, and acceptance record.

#### Scenario: Full traceability
- **WHEN** a GET request is made for package traceability
- **THEN** the response includes the package, all model versions (with parent experiments and their dataset versions), all dataset versions, and the acceptance record if exists

### Requirement: List delivery packages by project
The system SHALL return all delivery packages for a project, ordered by `created_at` descending.

#### Scenario: Ordered list
- **WHEN** a GET request is made to `/api/v1/projects/{project_id}/delivery-packages`
- **THEN** the response contains all packages sorted by `created_at` descending
