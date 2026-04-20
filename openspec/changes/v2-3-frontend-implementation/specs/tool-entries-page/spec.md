## ADDED Requirements

### Requirement: Tool entries list page with status tabs
The system SHALL display a tool entries list page at `/tools/entries` with status tab filtering: all, pending, in_progress, done, backfilled.

#### Scenario: List with data renders table
- **WHEN** user navigates to `/tools/entries` and API returns records
- **THEN** system renders el-table with columns: action name, tool name, status tag, backfilled mark, notes, actions

#### Scenario: Empty tab shows contextual empty state
- **WHEN** current tab has no records
- **THEN** system displays `<el-empty>` with description matching the tab status (e.g. "暂无待处理工具记录")

#### Scenario: Status tab filter works
- **WHEN** user clicks a status tab
- **THEN** system calls `GET /api/v1/tool-entries?status={status}` and filters the list

### Requirement: Tool entry create/edit form
The system SHALL provide a form dialog for creating/editing tool entries with fields: action_name (required), tool_name (required), status (select), is_backfilled (switch), notes (optional).

#### Scenario: Create new tool entry
- **WHEN** user fills form and submits
- **THEN** system calls `POST /api/v1/tool-entries` and refreshes list

#### Scenario: Edit existing tool entry
- **WHEN** user clicks edit on a row and modifies form
- **THEN** system calls `PUT /api/v1/tool-entries/{id}` and refreshes list

### Requirement: Quick status update buttons
The system SHALL provide quick action buttons in the table for status updates without opening the edit dialog.

#### Scenario: Mark as done button
- **WHEN** a tool entry status is "in_progress"
- **THEN** system shows "标记已完成" button in actions column
- **WHEN** clicked, system calls `PUT /api/v1/tool-entries/{id}` with status="done"

#### Scenario: Mark as backfilled button
- **WHEN** a tool entry status is "done" and is_backfilled is false
- **THEN** system shows "标记已回填" button in actions column
- **WHEN** clicked, system calls `PUT /api/v1/tool-entries/{id}` with is_backfilled=true

#### Scenario: No quick button for terminal states
- **WHEN** a tool entry is already backfilled
- **THEN** no quick status update buttons are shown

### Requirement: Tool entry status enum alignment
The system SHALL define TOOL_ENTRY_STATUSES in `status.js` with values exactly matching backend `constants.py` TOOL_STATUS_* definitions.
