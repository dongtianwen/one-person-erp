## ADDED Requirements

### Requirement: Leads list page with status tabs
The system SHALL display a leads list page at `/leads` with status tab filtering: all, initial, intent_confirmed, converted, invalid.

#### Scenario: List with data renders table
- **WHEN** user navigates to `/leads` and API returns records
- **THEN** system renders el-table with columns: source, status tag, next action, associated client, associated project, created time, actions

#### Scenario: Empty tab shows contextual empty state
- **WHEN** current tab has no records
- **THEN** system displays `<el-empty>` with description matching the tab status

#### Scenario: Status tab filter works
- **WHEN** user clicks a status tab
- **THEN** system calls `GET /api/v1/leads?status={status}` and filters the list

### Requirement: Lead create/edit form with dynamic selectors
The system SHALL provide a form dialog for creating/editing leads with fields: source (required), status (required), next_action (required), client_id (optional, dynamic load), project_id (optional, dynamic load), notes (optional).

#### Scenario: Dynamic client/project selector loading
- **WHEN** form dialog opens
- **THEN** system parallel-loads `GET /api/v1/customers` and `GET /api/v1/projects` for selector options
- **THEN** shows loading state during fetch

#### Scenario: Selector load failure disables and hints
- **WHEN** client or project API call fails
- **THEN** corresponding selector is disabled with hint "加载失败"

### Requirement: Quick status advance button
The system SHALL provide a "推进到下一阶段" quick button in the table for non-terminal leads.

#### Scenario: Advance from initial to intent_confirmed
- **WHEN** lead status is "initial"
- **THEN** system shows "推进到下一阶段" button
- **WHEN** clicked, confirmation dialog appears, on confirm system calls `PUT /api/v1/leads/{id}` with status="intent_confirmed"

#### Scenario: Advance from intent_confirmed to converted
- **WHEN** lead status is "intent_confirmed"
- **THEN** system shows "推进到下一阶段" button
- **WHEN** clicked, on confirm system calls `PUT /api/v1/leads/{id}` with status="converted"

#### Scenario: No advance button for terminal states
- **WHEN** lead status is "converted" or "invalid"
- **THEN** no advance button is shown

### Requirement: Lead status enum alignment
The system SHALL define LEAD_STATUSES in `status.js` with values exactly matching backend `constants.py` LEAD_STATUS_* definitions.
