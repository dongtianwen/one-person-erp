## ADDED Requirements

### Requirement: Dashboard help content
The system SHALL include a help entry for the Dashboard page in `help.js` with page description and metric group explanations.

#### Scenario: Dashboard help drawer accessible
- **WHEN** user clicks help button on Dashboard page
- **THEN** help drawer opens showing page description and six metric group explanations (customers, projects, contracts, finance, delivery, reminders)

### Requirement: Minutes help content
The system SHALL include help entries for the Minutes page in `help.js` with page description, seven field tips, and version compare explanation.

#### Scenario: Minutes page help drawer accessible
- **WHEN** user clicks help button on Minutes page
- **THEN** help drawer opens showing page description about meeting minutes traceability

#### Scenario: Minutes field tips accessible
- **WHEN** user hovers FieldTip on minutes form fields
- **THEN** tips display for: title, participants, conclusions, action_items, risk_points, project, client

#### Scenario: Version compare help accessible
- **WHEN** user views version compare dialog
- **THEN** help content explains snapshot auto-save and orange highlight for changes

### Requirement: Tool entries help content
The system SHALL include help entries for the Tool Entries page in `help.js` with page description and four field tips.

#### Scenario: Tool entries page help drawer accessible
- **WHEN** user clicks help button on Tool Entries page
- **THEN** help drawer opens showing page description about tracking external tool usage

#### Scenario: Tool entry field tips accessible
- **WHEN** user hovers FieldTip on tool entry form fields
- **THEN** tips display for: action_name, tool_name, status, is_backfilled

### Requirement: Leads help content
The system SHALL include help entries for the Leads page in `help.js` with page description and five field tips.

#### Scenario: Leads page help drawer accessible
- **WHEN** user clicks help button on Leads page
- **THEN** help drawer opens showing page description about tracking potential client follow-ups

#### Scenario: Lead field tips accessible
- **WHEN** user hovers FieldTip on lead form fields
- **THEN** tips display for: source, status, next_action, client, project
