## MODIFIED Requirements

### Requirement: Finance record creation with category-dependent validation
The system SHALL validate finance records differently based on category. When category is `outsourcing`, outsource_name, has_invoice, and tax_treatment MUST be non-NULL. When category is NOT outsourcing, those three fields SHALL be forced to NULL. When invoice_no is non-empty, invoice_direction, invoice_type, tax_rate MUST be non-NULL and tax_amount SHALL be calculated server-side. When invoice_no is empty, all four invoice fields SHALL be forced to NULL. These rules MUST apply identically to both POST (create) and PUT/PATCH (update) endpoints.

#### Scenario: Create with outsourcing category validates outsource fields
- **WHEN** POST /api/v1/finance/ with category=outsourcing
- **THEN** outsource_name, has_invoice, tax_treatment are all required

#### Scenario: Create with non-outsourcing category clears outsource fields
- **WHEN** POST /api/v1/finance/ with category != outsourcing
- **THEN** outsource_name, has_invoice, tax_treatment are stored as NULL

#### Scenario: Update switching category to non-outsourcing clears fields
- **WHEN** PUT /api/v1/finance/{id} changes category from outsourcing to other
- **THEN** outsource fields are cleared to NULL

#### Scenario: Update switching category to outsourcing validates fields
- **WHEN** PUT /api/v1/finance/{id} changes category to outsourcing with missing fields
- **THEN** HTTP 422 returned

#### Scenario: Create with invoice_no validates invoice fields
- **WHEN** POST /api/v1/finance/ with invoice_no non-empty
- **THEN** invoice_direction, invoice_type, tax_rate are required and tax_amount is auto-calculated

#### Scenario: Create without invoice_no clears invoice fields
- **WHEN** POST /api/v1/finance/ with invoice_no empty
- **THEN** invoice_direction, invoice_type, tax_rate, tax_amount are stored as NULL
