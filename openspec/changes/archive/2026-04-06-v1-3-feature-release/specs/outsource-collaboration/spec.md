## ADDED Requirements

### Requirement: Outsource category with mandatory fields
When a finance record's category is `outsourcing`, the system SHALL require three additional fields: `outsource_name` (string, max 200), `has_invoice` (boolean), and `tax_treatment` (enum: invoiced / withholding / none). All three MUST be non-NULL.

#### Scenario: Create outsource record with all fields
- **WHEN** POST /api/v1/finance/ with category=outsourcing and all three outsource fields filled
- **THEN** system creates the record successfully with HTTP 200

#### Scenario: Create outsource record missing outsource_name
- **WHEN** POST /api/v1/finance/ with category=outsourcing and outsource_name is NULL
- **THEN** system returns HTTP 422 with detail "外包费用必须填写外包方姓名"

#### Scenario: Create outsource record missing has_invoice
- **WHEN** POST /api/v1/finance/ with category=outsourcing and has_invoice is NULL
- **THEN** system returns HTTP 422 with detail "外包费用必须填写是否取得发票"

#### Scenario: Create outsource record missing tax_treatment
- **WHEN** POST /api/v1/finance/ with category=outsourcing and tax_treatment is NULL
- **THEN** system returns HTTP 422 with detail "外包费用必须填写税务处理方式"

### Requirement: Non-outsource category clears outsource fields
When a finance record's category is NOT `outsourcing`, the system SHALL force outsource_name, has_invoice, and tax_treatment to NULL regardless of client-provided values. This rule MUST apply to both create (POST) and update (PUT/PATCH) endpoints.

#### Scenario: Create non-outsource record ignores outsource fields
- **WHEN** POST /api/v1/finance/ with category != outsourcing and outsource fields provided
- **THEN** system stores NULL for all three outsource fields

#### Scenario: Update record switching from outsourcing to other category
- **WHEN** PUT /api/v1/finance/{id} changes category from outsourcing to another category
- **THEN** system clears all three outsource fields to NULL

#### Scenario: Update outsource record validates fields
- **WHEN** PUT /api/v1/finance/{id} with category=outsourcing and missing required outsource field
- **THEN** system returns HTTP 422 with appropriate error message
