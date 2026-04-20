## ADDED Requirements

### Requirement: Minutes list page
The system SHALL display a minutes list page at `/minutes` showing all meeting minutes with columns: title, associated project, associated client, created time, actions.

#### Scenario: List with data renders table
- **WHEN** user navigates to `/minutes` and API returns records
- **THEN** system renders el-table with all columns

#### Scenario: Empty list shows empty state
- **WHEN** API returns empty list
- **THEN** system displays `<el-empty description="暂无会议纪要" />`

#### Scenario: Filter by project or client
- **WHEN** user selects a project or client filter
- **THEN** system filters the minutes list accordingly

### Requirement: Minutes create/edit form with dual selector validation
The system SHALL provide a form dialog for creating/editing minutes with fields: title (required), participants, conclusions (required), action_items, risk_points, project_id (optional), client_id (optional).

#### Scenario: Both project and client empty blocks submission
- **WHEN** user submits form with both project_id and client_id empty
- **THEN** form validation fails with message "请关联项目或客户"

#### Scenario: At least one selector filled allows submission
- **WHEN** user fills project_id or client_id (or both)
- **THEN** form validation passes and submission proceeds

### Requirement: Minutes detail page with version history
The system SHALL display a minutes detail page at `/minutes/:id` showing all five content fields plus a version history panel.

#### Scenario: Version history panel shows snapshots
- **WHEN** user views a minute with snapshot history
- **THEN** system calls `GET /api/v1/snapshots/minutes/{id}/history` and renders version list with version number, time, and compare button

#### Scenario: No snapshot history shows placeholder
- **WHEN** snapshot history API returns empty list
- **THEN** system displays "暂无历史版本"

### Requirement: Version compare dialog
The system SHALL provide a version compare dialog that allows selecting any two versions and displays field-level differences.

#### Scenario: Open compare dialog with default versions
- **WHEN** user clicks compare button
- **THEN** dialog opens with latest version and previous version pre-selected
- **THEN** system calls diff API and renders comparison table

#### Scenario: Changed field highlighted
- **WHEN** a field value differs between two versions
- **THEN** that row background is highlighted with `#fff7e6` and shows "已变更" badge

#### Scenario: Unchanged field normal display
- **WHEN** a field value is identical between two versions
- **THEN** that row displays normally without highlight

#### Scenario: Switch versions re-fetches diff
- **WHEN** user changes version selection in either dropdown
- **THEN** system re-calls diff API and updates comparison table

#### Scenario: Diff API failure shows error
- **WHEN** diff API call fails
- **THEN** dialog displays "版本对比加载失败，请重试"

### Requirement: VersionCompareTable is reusable
The VersionCompareTable component SHALL accept schema prop to support different entity types (minutes, report, template).

#### Scenario: Pass minutes schema
- **WHEN** VersionCompareTable receives minutes schema with 5 fields
- **THEN** table renders 5 rows matching the schema

#### Scenario: Pass report schema
- **WHEN** VersionCompareTable receives report schema
- **THEN** table renders rows matching report fields
