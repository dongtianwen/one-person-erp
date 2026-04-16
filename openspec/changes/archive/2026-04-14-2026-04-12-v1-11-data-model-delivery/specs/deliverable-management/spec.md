## MODIFIED Requirements

### Requirement: Create deliverable record
The system SHALL allow creating deliverable records for a project. When `deliverable_type = account_handover`, the request body MAY include an `account_handovers` array. The `delivery_package_id` field MAY be provided to associate the deliverable with a delivery package.

#### Scenario: Create source code deliverable
- **WHEN** a POST request creates a deliverable with `deliverable_type = source_code`
- **THEN** the deliverable record is created successfully without any handover entries

#### Scenario: Create account handover with valid accounts
- **WHEN** a POST request creates a deliverable with `deliverable_type = account_handover` and `account_handovers` containing entries with valid field names
- **THEN** the deliverable and all handover entries are created in the same transaction

#### Scenario: Create deliverable with delivery package
- **WHEN** a POST request creates a deliverable with a valid `delivery_package_id`
- **THEN** the deliverable is created with `delivery_package_id` referencing the package

## ADDED Requirements

### Requirement: Delivery package deliverable association
The system SHALL allow associating deliverables with delivery packages via the `delivery_package_id` optional foreign key.

#### Scenario: List deliverables by package
- **WHEN** a GET request is made to `/api/v1/delivery-packages/{package_id}/deliverables`
- **THEN** the response contains all deliverables associated with the package

#### Scenario: Deliverable detail includes package reference
- **WHEN** a GET request retrieves a deliverable with a `delivery_package_id`
- **THEN** the response includes the `delivery_package_id` field
