## ADDED Requirements

### Requirement: Project close conditions checklist
The system SHALL enforce that all conditions must be met before a project can be closed.

#### Scenario: All milestones completed check
- **WHEN** evaluating project close conditions
- **THEN** all_milestones_completed SHALL be true only if all milestones have status "completed"
- **AND** if any milestone is not "completed", all_milestones_completed SHALL be false

#### Scenario: Final acceptance passed check
- **WHEN** evaluating project close conditions
- **THEN** final_acceptance_passed SHALL be determined by:
  - Querying the acceptances table for records where project_id matches and acceptance_type = "final"
  - Taking the most recent record by created_at
  - Checking if that record's status = "passed"
- **AND** if no final acceptance record exists, final_acceptance_passed SHALL be false
- **AND** the latest record's status SHALL be used (not any record)

#### Scenario: Payment cleared check
- **WHEN** evaluating project close conditions
- **THEN** payment_cleared SHALL be true only if:
  - All milestones have payment_status = "received"
  - OR all milestones have payment_amount = 0
- **AND** if any milestone has payment_status != "received" and payment_amount > 0, payment_cleared SHALL be false

#### Scenario: Deliverables archived check
- **WHEN** evaluating project close conditions
- **THEN** deliverables_archived SHALL be true only if at least one deliverable record exists for the project
- **AND** if no deliverable records exist, deliverables_archived SHALL be false

### Requirement: Close check endpoint
The system SHALL provide a read-only endpoint to check project close conditions.

#### Scenario: Close check returns all conditions
- **WHEN** a user requests the close check for a project
- **THEN** the system SHALL return:
  - all_milestones_completed: boolean
  - final_acceptance_passed: boolean
  - payment_cleared: boolean
  - deliverables_archived: boolean
  - can_close: boolean (true only if all above are true)
  - blocking_items: array of condition names that are not satisfied

#### Scenario: Close check when all conditions met
- **WHEN** all close conditions are satisfied
- **THEN** can_close SHALL be true
- **AND** blocking_items SHALL be an empty array

#### Scenario: Close check when conditions not met
- **WHEN** one or more close conditions are not satisfied
- **THEN** can_close SHALL be false
- **AND** blocking_items SHALL contain the names of unsatisfied conditions

### Requirement: Project close execution
The system SHALL close a project only when all conditions are met.

#### Scenario: Close blocked when milestone not completed
- **WHEN** a user attempts to close a project with an incomplete milestone
- **THEN** the system SHALL return HTTP 409
- **AND** the error message SHALL list "all_milestones_completed" as a blocking condition

#### Scenario: Close blocked when no final acceptance
- **WHEN** a user attempts to close a project with no final acceptance record
- **THEN** the system SHALL return HTTP 409
- **AND** the error message SHALL list "final_acceptance_passed" as a blocking condition

#### Scenario: Close blocked when final acceptance not passed
- **WHEN** a user attempts to close a project where the latest final acceptance has status != "passed"
- **THEN** the system SHALL return HTTP 409
- **AND** the error message SHALL list "final_acceptance_passed" as a blocking condition
- **AND** the system SHALL use the LATEST final acceptance record, not any passing record

#### Scenario: Close blocked when payment not cleared
- **WHEN** a user attempts to close a project with unpaid invoices
- **THEN** the system SHALL return HTTP 409
- **AND** the error message SHALL list "payment_cleared" as a blocking condition

#### Scenario: Close blocked when no deliverables
- **WHEN** a user attempts to close a project with no deliverable records
- **THEN** the system SHALL return HTTP 409
- **AND** the error message SHALL list "deliverables_archived" as a blocking condition

#### Scenario: Close success when all conditions met
- **WHEN** a user closes a project and all conditions are satisfied
- **THEN** the project status SHALL change to "completed"
- **AND** closed_at SHALL be set to current timestamp
- **AND** close_checklist SHALL be written as a JSON snapshot of all condition states
- **AND** the system SHALL return HTTP 200

#### Scenario: Close transaction atomic
- **WHEN** a project close operation fails after partial state change
- **THEN** all changes SHALL be rolled back
- **AND** the project SHALL remain in its previous state

### Requirement: Already closed project protection
The system SHALL prevent closing an already closed project.

#### Scenario: Close already closed project returns 409
- **WHEN** a user attempts to close a project with status "completed"
- **THEN** the system SHALL return HTTP 409
- **AND** the error message SHALL indicate "Project is already closed"

### Requirement: Closed project core fields immutable
The system SHALL prevent modification of core fields on closed projects.

#### Scenario: Modify closed project core field blocked
- **WHEN** a user attempts to modify a core field of a closed project
- **THEN** the system SHALL return HTTP 409
- **AND** the error message SHALL indicate "Cannot modify closed project"

#### Scenario: Core fields include name, customer_id, contract_id
- **WHEN** determining which fields are core fields
- **THEN** core fields SHALL include at least: name, customer_id, contract_id
- **AND** modification of these fields SHALL be blocked for closed projects

### Requirement: Project not found returns 404
The system SHALL return HTTP 404 when requesting operations on a non-existent project.

#### Scenario: Close check on non-existent project
- **WHEN** a user requests close check for a non-existent project_id
- **THEN** the system SHALL return HTTP 404
- **AND** the error message SHALL indicate "Project not found"
