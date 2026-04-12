## MODIFIED Requirements

### Requirement: Project detail response
The project detail endpoint SHALL include a `current_version` field in its response, showing the `version_no` of the release record with `is_current_online = True` for that project. When no such release exists, `current_version` SHALL be `null`.

#### Scenario: Current version present
- **WHEN** a GET request is made to `/api/v1/projects/{project_id}` and a release with `is_current_online = True` exists
- **THEN** the response includes `"current_version"` with the release's `version_no`

#### Scenario: Current version null
- **WHEN** a GET request is made to `/api/v1/projects/{project_id}` and no release with `is_current_online = True` exists
- **THEN** the response includes `"current_version": null`
