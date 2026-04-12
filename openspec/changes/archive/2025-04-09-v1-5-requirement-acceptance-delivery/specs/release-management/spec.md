## ADDED Requirements

### Requirement: Create release record with online uniqueness
The system SHALL allow creating release records. When `is_current_online = True`, all other releases of the same project SHALL have `is_current_online` set to `False` in the same transaction. Transaction failure SHALL cause full rollback.

#### Scenario: Create as current online
- **WHEN** a POST request creates a release with `is_current_online = True`
- **THEN** the release is created and all other releases of the same project have `is_current_online = False`

#### Scenario: No two current online after creation
- **WHEN** a new release is created with `is_current_online = True` for a project that already has a current online release
- **THEN** exactly one release has `is_current_online = True` after the transaction

#### Scenario: Transaction rollback on failure
- **WHEN** creating a release fails mid-transaction
- **THEN** no changes are persisted; the original current online release remains unchanged

### Requirement: Set release as current online
The system SHALL allow setting a specific release as the current online version. All other releases of the same project SHALL have `is_current_online` set to `False` in the same transaction.

#### Scenario: Switch current online
- **WHEN** a POST request is made to `/api/v1/projects/{project_id}/releases/{release_id}/set-online`
- **THEN** the specified release becomes the only one with `is_current_online = True`

#### Scenario: No two current online after switch
- **WHEN** a release is set as current online
- **THEN** no other release of the same project has `is_current_online = True`

### Requirement: List releases with pinning indicator
The system SHALL return all releases for a project, ordered by `release_date` descending. The release with `is_current_online = True` SHALL have `is_pinned: true` in the response.

#### Scenario: Ordered list with pin
- **WHEN** a GET request is made to `/api/v1/projects/{project_id}/releases`
- **THEN** releases are sorted by `release_date` descending, and the current online release has `is_pinned: true`

### Requirement: Release delete returns 405
The system SHALL return HTTP 405 for any DELETE request on release records.

#### Scenario: Delete rejection
- **WHEN** a DELETE request is made to `/api/v1/projects/{project_id}/releases/{release_id}`
- **THEN** the system returns HTTP 405

### Requirement: Release immutable fields
The `version_no` and `release_date` fields SHALL NOT be modifiable after creation via PUT or PATCH. `changelog` and `notes` SHALL always be modifiable.

#### Scenario: Reject version_no modification
- **WHEN** a PUT or PATCH request attempts to modify `version_no`
- **THEN** the system returns HTTP 422 with message "版本号和发布日期不可修改"

#### Scenario: Reject release_date modification
- **WHEN** a PUT or PATCH request attempts to modify `release_date`
- **THEN** the system returns HTTP 422 with message "版本号和发布日期不可修改"

#### Scenario: Allow changelog modification
- **WHEN** a PATCH request modifies `changelog`
- **THEN** the update succeeds

### Requirement: Project detail includes current version
The system SHALL include a `current_version` field in the project detail response, showing the `version_no` of the current online release. When no online release exists, `current_version` SHALL be `null`.

#### Scenario: Current version present
- **WHEN** a GET request is made to `/api/v1/projects/{project_id}` and a current online release exists
- **THEN** the response includes `"current_version": "v1.2.0"` (the version_no of the current online release)

#### Scenario: Current version null when none
- **WHEN** a GET request is made to `/api/v1/projects/{project_id}` and no current online release exists
- **THEN** the response includes `"current_version": null`
