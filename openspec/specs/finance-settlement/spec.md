# finance-settlement Specification

## Purpose
财务记录结算状态追踪，管理个人垫付和借款的结算流程。

## Requirements

### Requirement: Finance records SHALL track settlement status for advances and loans

When a finance record has `funding_source` of "personal_advance" (个人垫付) or "loan" (借款), the system SHALL require a `settlement_status` field. The settlement status SHALL be one of: "open" (未结清), "partial" (部分归还), "closed" (已结清). For other funding sources, `settlement_status` SHALL be NULL and ignored.

#### Scenario: Expense with personal advance requires settlement status
- **WHEN** user creates an expense record with `funding_source = "personal_advance"`
- **THEN** system requires `settlement_status` to be set
- **AND** rejects the request if `settlement_status` is missing

#### Scenario: Expense with loan requires settlement status
- **WHEN** user creates an expense record with `funding_source = "loan"`
- **THEN** system requires `settlement_status` to be set to "open"
- **AND** rejects the request if `settlement_status` is missing

#### Scenario: Income record does not require settlement status
- **WHEN** user creates an income record with any funding source
- **THEN** system does not require `settlement_status`
- **AND** stores it as NULL

### Requirement: Business note SHALL be required for personal advances and loans

When `funding_source` is "personal_advance" or "loan", the system SHALL require the `business_note` field (业务说明) to be filled with a description of the transaction (max 500 characters).

#### Scenario: Personal advance without business note is rejected
- **WHEN** user submits expense with `funding_source = "personal_advance"` and empty `business_note`
- **THEN** system rejects the request with validation error "业务说明为必填项"

### Requirement: Related record SHALL require related note and forbid self-reference

When a user fills in `related_record_id`, the system SHALL require `related_note` to be filled. The system SHALL reject self-referencing (a record cannot reference itself).

#### Scenario: Related record without note is rejected
- **WHEN** user sets `related_record_id` but leaves `related_note` empty
- **THEN** system rejects the request with validation error "关联说明为必填项"

#### Scenario: Self-reference is rejected
- **WHEN** user sets `related_record_id` to the same record's own ID
- **THEN** system rejects the request with validation error "禁止自关联"

### Requirement: Monthly report SHALL include funding source breakdown and unsettled summary

The monthly financial report SHALL include a funding source dimension summary showing totals per source. It SHALL also display the count and total amount of records with `settlement_status` of "open" and "partial".

#### Scenario: Monthly report shows unsettled advances
- **WHEN** user requests monthly report
- **THEN** response includes count and total amount of open/partial settlement records
- **AND** includes funding source breakdown totals

### Requirement: Dashboard SHALL show unsettled advance/loan warning

The dashboard SHALL display a warning metric showing the count and total amount of finance records with `settlement_status` of "open" or "partial".

#### Scenario: Dashboard displays unsettled warning
- **WHEN** user views dashboard
- **THEN** dashboard shows number of unsettled advance/loan records
- **AND** shows total unsettled amount
