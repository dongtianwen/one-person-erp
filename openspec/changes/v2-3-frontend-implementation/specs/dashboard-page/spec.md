## ADDED Requirements

### Requirement: Dashboard page displays six metric groups
The system SHALL display a Dashboard page at `/dashboard` with six Widget groups: customers, projects, contracts, finance, delivery, reminders. Each group displays two metric values.

#### Scenario: Page loads and fetches summary data
- **WHEN** user navigates to `/dashboard`
- **THEN** system calls `GET /api/v1/dashboard/summary` and renders six Widget groups

#### Scenario: Metric value is null displays placeholder
- **WHEN** a metric_value in the summary response is null
- **THEN** that metric item displays "暂无数据" instead of blank

#### Scenario: All metrics null does not crash page
- **WHEN** all metric_values in the summary response are null
- **THEN** page renders all six Widgets with "暂无数据", no console errors

### Requirement: Dashboard manual refresh
The system SHALL provide a manual refresh button that rebuilds dashboard data.

#### Scenario: Click refresh triggers rebuild
- **WHEN** user clicks the refresh button
- **THEN** system calls `POST /api/v1/dashboard/rebuild`, disables button and shows loading state
- **THEN** after rebuild completes, system re-fetches summary and updates all Widgets

#### Scenario: Rebuild response contains warning_code
- **WHEN** rebuild API response contains `warning_code`
- **THEN** system displays warning toast via `useApiWarning`

### Requirement: Dashboard constants alignment
The system SHALL define metric_key strings in `dashboard.js` that exactly match the backend `constants.py` METRIC_* definitions.

#### Scenario: Metric key matches backend
- **WHEN** frontend sends or receives metric_key values
- **THEN** all metric_key strings MUST be identical to backend constants.py definitions
