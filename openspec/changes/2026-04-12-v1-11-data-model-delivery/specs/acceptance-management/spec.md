## MODIFIED Requirements

### Requirement: Create acceptance record with reminder trigger
The system SHALL allow creating acceptance records. When `result` is `passed` or `conditional` AND `trigger_payment_reminder = True`, the system SHALL create a payment reminder in the `reminders` table within the same transaction. The `reminder_id` SHALL be written back to the acceptance record. When the acceptance is created via a delivery package endpoint (`/api/v1/delivery-packages/{package_id}/acceptance`), the `delivery_package_id` field MUST be provided and MUST match the current package. The `acceptance_type` SHALL be auto-determined: `model` if the package contains model versions, `dataset` if only dataset versions.

#### Scenario: Passed acceptance triggers reminder
- **WHEN** a POST request creates an acceptance with `result = passed` and `trigger_payment_reminder = True`
- **THEN** a reminder is created with `title = "收款提醒：{acceptance_name}"`, `type = custom`, `is_critical = False`, `status = pending`, and the `reminder_id` is written back to the acceptance record

#### Scenario: Conditional acceptance triggers reminder
- **WHEN** a POST request creates an acceptance with `result = conditional` and `trigger_payment_reminder = True`
- **THEN** a reminder is created and `reminder_id` written back

#### Scenario: Failed acceptance no reminder
- **WHEN** a POST request creates an acceptance with `result = failed`
- **THEN** no reminder is created, `reminder_id` remains NULL

#### Scenario: Reminder in same transaction
- **WHEN** the reminder creation fails after the acceptance record is created
- **THEN** both the acceptance and reminder are rolled back

#### Scenario: Reminder ID written back
- **WHEN** a reminder is created for an acceptance
- **THEN** the acceptance record's `reminder_id` field matches the created reminder's ID

## ADDED Requirements

### Requirement: Delivery package acceptance with type
The system SHALL support creating acceptance records through delivery packages. The `delivery_package_id` field MUST be non-null for delivery package acceptances. The `acceptance_type` field SHALL distinguish between traditional acceptances and delivery package acceptances with values `dataset` and `model`.

#### Scenario: Delivery package acceptance created
- **WHEN** an acceptance is created via the delivery package endpoint
- **THEN** the `delivery_package_id` is set to the package ID and `acceptance_type` is auto-determined

#### Scenario: Delivery package acceptance detail
- **WHEN** a GET request retrieves a delivery package acceptance
- **THEN** the response includes `delivery_package_id` and `acceptance_type` fields
