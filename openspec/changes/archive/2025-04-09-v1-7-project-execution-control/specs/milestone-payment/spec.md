## ADDED Requirements

### Requirement: Milestone payment amount on creation
The system SHALL allow setting payment_amount and payment_due_date when creating or updating a milestone.

#### Scenario: Set payment amount on milestone creation
- **WHEN** a user creates a milestone with payment_amount and payment_due_date
- **THEN** the milestone SHALL be created with the provided payment values
- **AND** payment_status SHALL default to "unpaid"

#### Scenario: Payment amount zero allowed
- **WHEN** a milestone is created with payment_amount = 0
- **THEN** the milestone SHALL be created successfully
- **AND** payment_status SHALL be set to "unpaid"

#### Scenario: Payment amount negative rejected
- **WHEN** a user attempts to create a milestone with payment_amount < 0
- **THEN** the system SHALL return HTTP 422
- **AND** the error message SHALL indicate that payment_amount must be non-negative

### Requirement: Payment status transitions
The system SHALL enforce strict payment status transitions based on milestone completion.

#### Scenario: Unpaid to invoiced requires milestone completion
- **WHEN** a user attempts to mark a milestone as "invoiced"
- **AND** the milestone status is NOT "completed"
- **THEN** the system SHALL return HTTP 409
- **AND** the error message SHALL indicate that only completed milestones can be invoiced

#### Scenario: Unpaid to invoiced succeeds when completed
- **WHEN** a user marks a completed milestone as "invoiced"
- **THEN** the payment_status SHALL change to "invoiced"
- **AND** the change SHALL be recorded

#### Scenario: Invoiced to received
- **WHEN** a user marks an invoiced milestone as "received"
- **THEN** the payment_status SHALL change to "received"
- **AND** payment_received_at SHALL be set to current timestamp

#### Scenario: Received is terminal
- **WHEN** a milestone has payment_status "received"
- **THEN** no further payment status transitions SHALL be allowed

#### Scenario: Direct to received blocked
- **WHEN** a user attempts to change payment_status from "unpaid" to "received"
- **THEN** the system SHALL return HTTP 409
- **AND** the error message SHALL indicate that milestones must be invoiced first

### Requirement: Payment summary
The system SHALL provide a payment summary for a project.

#### Scenario: Payment summary amounts are correct
- **WHEN** a user requests the payment summary for a project
- **THEN** the system SHALL return:
  - total_contract_amount: sum of all milestone payment_amount
  - received_amount: sum of received payments
  - invoiced_amount: sum of invoiced but not received payments
  - unpaid_amount: sum of unpaid payments
- **AND** all amounts SHALL be precise to 2 decimal places

#### Scenario: Payment summary includes overdue milestones
- **WHEN** a user requests the payment summary for a project
- **THEN** the system SHALL return overdue_milestones array
- **AND** overdue milestones SHALL include those where:
  - payment_due_date < current date
  - payment_status != "received"
- **AND** overdue milestones SHALL be ordered by payment_due_date ASC

### Requirement: Milestone not found returns 404
The system SHALL return HTTP 404 when requesting a non-existent milestone.

#### Scenario: Payment update on non-existent milestone
- **WHEN** a user attempts to update payment status for a non-existent milestone_id
- **THEN** the system SHALL return HTTP 404
- **AND** the error message SHALL indicate "Milestone not found"
