# contract-generation Specification

## Purpose
TBD - created by archiving change v1-12-quotation-contract-generation. Update Purpose after archive.
## Requirements
### Requirement: System generates contract content from quotation
The system SHALL allow users to create a contract draft from an accepted quotation with generated content.

#### Scenario: Create contract from quotation
- **WHEN** client requests POST /api/v1/quotations/{id}/generate-contract
- **THEN** system SHALL check if quotation exists
- **THEN** system SHALL check if quotation.status = "accepted" (quotation must be accepted before contract generation)
- **THEN** system SHALL check if quotation has already been converted to contract (check converted_contract_id)
- **THEN** if already converted, system SHALL return error with code QUOTE_ALREADY_CONVERTED
- **THEN** if conversion conditions met, system SHALL create contract with status=draft, template_id from default template, and generated content from rendering
- **THEN** system SHALL update quotation.converted_contract_id with new contract_id

#### Scenario: Contract generation uses default template
- **WHEN** creating contract from quotation
- **THEN** system SHALL use default contract template from templates table
- **THEN** system SHALL render template with contract context (contract_no, customer_name, project_name, total_amount, sign_date, company_name, quotation_no, etc.)

#### Scenario: Deliverables description comes from user input
- **WHEN** rendering contract template
- **THEN** system SHALL use deliverables_desc from template variable (default empty string)
- **THEN** system SHALL NOT extract deliverables content from deliverables table
- **THEN** user SHALL manually fill deliverables_desc in template or before contract generation

### Requirement: System allows regenerating contract content
The system SHALL provide endpoint to regenerate contract content with optional force parameter.

#### Scenario: Regenerate when no existing content
- **WHEN** client requests POST /api/v1/contracts/{id}/generate?force=false
- **THEN** if generated_content is NULL, system SHALL generate new content

#### Scenario: Reject regeneration when content exists without force
- **WHEN** client requests POST /api/v1/contracts/{id}/generate?force=false
- **THEN** if generated_content is NOT NULL and force=false, system SHALL return error CONTENT_ALREADY_EXISTS
- **THEN** response SHALL include existing generated_content in body

#### Scenario: Regenerate when content exists with force=true
- **WHEN** client requests POST /api/v1/contracts/{id}/generate?force=true
- **THEN** if generated_content is NOT NULL, system SHALL overwrite existing content
- **THEN** system SHALL update content_generated_at to current timestamp
- **THEN** template_id SHALL remain unchanged

#### Scenario: Reject regeneration when content is frozen
- **WHEN** client requests POST /api/v1/contracts/{id}/generate?force=true
- **THEN** if contract.status = "active", system SHALL return error CONTENT_FROZEN
- **THEN** system SHALL reject regardless of force parameter

#### Scenario: Reject regeneration when quotation_id is NULL
- **WHEN** client requests POST /api/v1/contracts/{id}/generate?force=true
- **THEN** if contract.quotation_id is NULL, system SHALL return error QUOTE_NO_QUOTATION_ID
- **THEN** system SHALL reject regardless of force parameter

#### Scenario: Regenerate updates content_generated_at
- **WHEN** regenerating contract content with force=true
- **THEN** system SHALL update content_generated_at to current timestamp

### Requirement: System provides contract preview
The system SHALL allow users to preview contract content without persisting changes.

#### Scenario: Preview contract content
- **WHEN** client requests GET /api/v1/contracts/{id}/preview
- **THEN** system SHALL render contract template with current context
- **THEN** system SHALL return generated content in response body
- **THEN** system SHALL NOT write to database

#### Scenario: Preview allowed when content is frozen
- **WHEN** client requests GET /api/v1/contracts/{id}/preview
- **THEN** system SHALL return preview even if contract.status = "active"
- **THEN** system SHALL NOT modify database state

### Requirement: System allows manual editing of contract content
The system SHALL provide endpoint to manually edit contract generated content.

#### Scenario: Manual edit successful
- **WHEN** client requests PUT /api/v1/contracts/{id}/generated-content with new content
- **THEN** system SHALL update generated_content with new content
- **THEN** system SHALL NOT update content_generated_at
- **THEN** system SHALL NOT regenerate content from template

#### Scenario: Reject manual edit when content is frozen
- **WHEN** client requests PUT /api/v1/contracts/{id}/generated-content
- **THEN** if contract.status = "active", system SHALL return error CONTENT_FROZEN
- **THEN** system SHALL NOT modify database

#### Scenario: Manual edit preserves template_id
- **WHEN** client manually edits contract content
- **THEN** system SHALL keep the existing template_id unchanged
- **THEN** template_id SHALL remain linked to the source template

### Requirement: System enforces contract creation from accepted quotation
The system SHALL ensure contracts can only be created from accepted quotations.

#### Scenario: Reject contract creation from non-accepted quotation
- **WHEN** client requests POST /api/v1/quotations/{id}/generate-contract
- **THEN** if quotation.status != "accepted", system SHALL return error with code (e.g., QUOTATION_NOT_ACCEPTED)
- **THEN** system SHALL NOT create contract

#### Scenario: Contract creation atomic operation
- **WHEN** client requests POST /api/v1/quotations/{id}/generate-contract
- **THEN** system SHALL perform all operations in a single transaction:
  1. Create contract record with status=draft, generated_content, content_generated_at
  2. Update quotation.converted_contract_id with new contract_id
- **THEN** if any operation fails, system SHALL rollback all changes
- **THEN** system SHALL ensure data consistency

