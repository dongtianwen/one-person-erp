## ADDED Requirements

### Requirement: Requirements freeze on quotation acceptance
The system SHALL automatically freeze project requirements when the associated quotation status changes to "accepted".

#### Scenario: Requirements not frozen before quotation accepted
- **WHEN** a project has an active quotation with status "pending" or "draft"
- **THEN** the project requirements SHALL NOT be frozen
- **AND** direct requirement edits SHALL be allowed

#### Scenario: Requirements freeze on quotation acceptance
- **WHEN** a quotation associated with a project changes status to "accepted"
- **THEN** the project requirements SHALL become frozen
- **AND** subsequent direct requirement edits SHALL be blocked

### Requirement: Direct requirement edit blocked when frozen
The system SHALL return HTTP 409 when attempting to directly edit frozen requirements.

#### Scenario: Direct edit blocked with clear error message
- **WHEN** a user attempts to edit a frozen requirement via direct API
- **THEN** the system SHALL return HTTP 409
- **AND** the error message SHALL state "需求已冻结，请通过变更单提交"

### Requirement: Change order creation
The system SHALL allow creation of change orders for frozen projects.

#### Scenario: Create change order for frozen project
- **WHEN** a user creates a change order for a frozen project
- **THEN** the system SHALL create the change order with status "pending"
- **AND** the change order SHALL include extra_days, extra_amount, and description

#### Scenario: Extra amount zero allowed
- **WHEN** a change order is created with extra_amount = 0
- **THEN** the system SHALL accept the change order
- **AND** the extra_amount SHALL be stored as 0.00

#### Scenario: Extra amount negative rejected
- **WHEN** a change order is created with extra_amount < 0
- **THEN** the system SHALL return HTTP 422
- **AND** the error message SHALL indicate that extra_amount must be non-negative

### Requirement: Change order status transitions
The system SHALL enforce strict status transitions for change orders.

#### Scenario: Pending to confirmed transition
- **WHEN** a change order with status "pending" is confirmed
- **THEN** the status SHALL change to "confirmed"
- **AND** client_confirmed_at SHALL be set to current timestamp
- **AND** the requirement changes SHALL be applied to the project

#### Scenario: Pending to rejected transition
- **WHEN** a change order with status "pending" is rejected
- **THEN** the status SHALL change to "rejected"
- **AND** client_rejected_at SHALL be set to current timestamp
- **AND** rejection_reason SHALL be stored

#### Scenario: Pending to cancelled transition
- **WHEN** a change order with status "pending" is cancelled
- **THEN** the status SHALL change to "cancelled"
- **AND** no changes SHALL be applied to the project

#### Scenario: Confirmed is terminal
- **WHEN** a change order has status "confirmed"
- **THEN** no further status transitions SHALL be allowed

#### Scenario: Rejected is terminal
- **WHEN** a change order has status "rejected"
- **THEN** no further status transitions SHALL be allowed

#### Scenario: Cancelled is terminal
- **WHEN** a change order has status "cancelled"
- **THEN** no further status transitions SHALL be allowed

### Requirement: Requirement changes snapshot
The system SHALL write a requirement_changes snapshot when a change order is confirmed.

#### Scenario: Snapshot written on confirmation
- **WHEN** a change order is confirmed
- **THEN** a requirement_changes snapshot SHALL be written
- **AND** the snapshot SHALL include the old and new values of changed fields
- **AND** the snapshot SHALL reference the change_order_id

### Requirement: Change order list and detail
The system SHALL provide APIs to list and retrieve change orders.

#### Scenario: List change orders for project
- **WHEN** a user requests change orders for a project
- **THEN** the system SHALL return all change orders for that project
- **AND** the results SHALL be ordered by created_at DESC

#### Scenario: Get change order detail
- **WHEN** a user requests a specific change order by ID
- **THEN** the system SHALL return the change order details
- **OR** return HTTP 404 if not found

### Requirement: Only confirmed changes affect development
The system SHALL only allow confirmed change orders to be associated with milestones.

#### Scenario: Pending change cannot link to milestone
- **WHEN** a user attempts to link a pending change order to a milestone
- **THEN** the system SHALL return HTTP 409
- **AND** the error message SHALL indicate that only confirmed changes can be linked

#### Scenario: Confirmed change can link to milestone
- **WHEN** a user links a confirmed change order to a milestone
- **THEN** the association SHALL be created successfully
