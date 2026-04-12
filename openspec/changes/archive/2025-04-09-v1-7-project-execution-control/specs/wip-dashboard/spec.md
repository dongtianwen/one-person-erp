## ADDED Requirements

### Requirement: WIP dashboard displays active projects
The system SHALL display all active projects on the WIP dashboard.

#### Scenario: Dashboard shows all active projects
- **WHEN** a user views the WIP dashboard
- **THEN** the system SHALL display all projects with status "active"
- **AND** each project card SHALL show at least: project name, customer name, start date

### Requirement: WIP count warning display
The system SHALL display a warning when the number of active projects exceeds WIP_DISPLAY_LIMIT.

#### Scenario: Warning displayed when WIP exceeds limit
- **WHEN** the number of active projects > WIP_DISPLAY_LIMIT (2)
- **THEN** the system SHALL display a yellow warning message
- **AND** the message SHALL state "当前有 N 个项目并行，注意精力分配"
- **AND** N SHALL be the actual count of active projects

#### Scenario: No warning when WIP within limit
- **WHEN** the number of active projects <= WIP_DISPLAY_LIMIT (2)
- **THEN** the system SHALL NOT display a WIP warning message

### Requirement: WIP limit is display-only
The system SHALL NOT use WIP limit to block any operations.

#### Scenario: Create project allowed when WIP exceeds limit
- **WHEN** a user attempts to create a new project
- **AND** the current WIP count already exceeds WIP_DISPLAY_LIMIT
- **THEN** the system SHALL allow the project creation
- **AND** no WIP-related validation SHALL occur

#### Scenario: Start project allowed when WIP exceeds limit
- **WHEN** a user attempts to start a project (change status to "active")
- **AND** the current WIP count already exceeds WIP_DISPLAY_LIMIT
- **THEN** the system SHALL allow the status change
- **AND** no WIP-related validation SHALL occur

#### Scenario: Convert to contract allowed when WIP exceeds limit
- **WHEN** a user attempts to convert a quotation to a contract
- **AND** the current WIP count already exceeds WIP_DISPLAY_LIMIT
- **THEN** the system SHALL allow the conversion
- **AND** no WIP-related validation SHALL occur

#### Scenario: All business operations ignore WIP limit
- **WHEN** any business operation is attempted (create project, update milestone, modify requirements, etc.)
- **THEN** the WIP_DISPLAY_LIMIT constant SHALL NOT be referenced in any backend validation logic
- **AND** the operation SHALL succeed or fail based on business rules, not WIP count

### Requirement: WIP_DISPLAY_LIMIT constant location
The WIP_DISPLAY_LIMIT constant SHALL only be referenced in frontend dashboard display code.

#### Scenario: Constant defined in core constants
- **WHEN** WIP_DISPLAY_LIMIT is needed
- **THEN** it SHALL be defined in backend/core/constants.py
- **AND** it SHALL have a value of 2
- **AND** a comment SHALL clarify it is for display purposes only

#### Scenario: Backend validation does not use WIP limit
- **WHEN** reviewing backend validation code
- **THEN** WIP_DISPLAY_LIMIT SHALL NOT appear in any validation logic
- **AND** no API endpoint SHALL reject a request based on WIP count

### Requirement: Frontend WIP warning behavior
The frontend SHALL display the WIP warning without blocking any UI actions.

#### Scenario: Warning visible but buttons enabled
- **WHEN** the WIP warning is displayed
- **THEN** all action buttons (create project, start project, etc.) SHALL remain enabled
- **AND** no UI elements SHALL be disabled due to WIP count

#### Scenario: Warning updates dynamically
- **WHEN** a project status changes to/from "active"
- **THEN** the WIP count SHALL update immediately
- **AND** the warning SHALL appear or disappear based on the new count
