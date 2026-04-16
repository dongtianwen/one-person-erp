# quotation-generation Specification

## Purpose
TBD - created by archiving change v1-12-quotation-contract-generation. Update Purpose after archive.
## Requirements
### Requirement: System generates quotation content from project
The system SHALL allow users to create a quotation draft with generated content from a project.

#### Scenario: Create quotation from project
- **WHEN** client requests POST /api/v1/projects/{id}/generate-quotation
- **THEN** system SHALL check if project has existing draft quotation (status=draft AND template_id IS NOT NULL)
- **THEN** if draft exists, system SHALL return error DRAFT_ALREADY_EXISTS with existing quotation_id
- **THEN** if no draft exists, system SHALL create quotation with status=draft, template_id from default template, and generated content from rendering

#### Scenario: Quotation generation uses default template
- **WHEN** creating quotation from project
- **THEN** system SHALL use default quotation template from templates table
- **THEN** system SHALL render template with quotation context (quotation_no, customer_name, project_name, requirement_summary, estimate_days, total_amount, valid_until, created_date)

#### Scenario: Optional variables in quotation generation
- **WHEN** rendering quotation template
- **THEN** system SHALL include optional variables daily_rate, direct_cost, risk_buffer_rate, tax_rate, tax_amount, discount_amount, subtotal_amount if present
- **THEN** system SHALL use empty string for missing optional variables

### Requirement: System allows regenerating quotation content
The system SHALL provide endpoint to regenerate quotation content with optional force parameter.

#### Scenario: Regenerate when no existing content
- **WHEN** client requests POST /api/v1/quotations/{id}/generate?force=false
- **THEN** if generated_content is NULL, system SHALL generate new content

#### Scenario: Reject regeneration when content exists without force
- **WHEN** client requests POST /api/v1/quotations/{id}/generate?force=false
- **THEN** if generated_content is NOT NULL and force=false, system SHALL return error CONTENT_ALREADY_EXISTS
- **THEN** response SHALL include existing generated_content in body

#### Scenario: Regenerate when content exists with force=true
- **WHEN** client requests POST /api/v1/quotations/{id}/generate?force=true
- **THEN** if generated_content is NOT NULL, system SHALL overwrite existing content
- **THEN** system SHALL update content_generated_at to current timestamp
- **THEN** template_id SHALL remain unchanged

#### Scenario: Reject regeneration when content is frozen
- **WHEN** client requests POST /api/v1/quotations/{id}/generate?force=true
- **THEN** if quotation.status = "accepted", system SHALL return error CONTENT_FROZEN
- **THEN** system SHALL reject regardless of force parameter

#### Scenario: Regenerate updates content_generated_at
- **WHEN** regenerating quotation content with force=true
- **THEN** system SHALL update content_generated_at to current timestamp

### Requirement: System provides quotation preview
The system SHALL allow users to preview quotation content without persisting changes.

#### Scenario: Preview quotation content
- **WHEN** client requests GET /api/v1/quotations/{id}/preview
- **THEN** system SHALL render quotation template with current context
- **THEN** system SHALL return generated content in response body
- **THEN** system SHALL NOT write to database

#### Scenario: Preview allowed when content is frozen
- **WHEN** client requests GET /api/v1/quotations/{id}/preview
- **THEN** system SHALL return preview even if quotation.status = "accepted"
- **THEN** system SHALL NOT modify database state

### Requirement: System allows manual editing of quotation content
The system SHALL provide endpoint to manually edit quotation generated content.

#### Scenario: Manual edit successful
- **WHEN** client requests PUT /api/v1/quotations/{id}/generated-content with new content
- **THEN** system SHALL update generated_content with new content
- **THEN** system SHALL NOT update content_generated_at
- **THEN** system SHALL NOT regenerate content from template

#### Scenario: Reject manual edit when content is frozen
- **WHEN** client requests PUT /api/v1/quotations/{id}/generated-content
- **THEN** if quotation.status = "accepted", system SHALL return error CONTENT_FROZEN
- **THEN** system SHALL NOT modify database

#### Scenario: Manual edit preserves template_id
- **WHEN** client manually edits quotation content
- **THEN** system SHALL keep the existing template_id unchanged
- **THEN** template_id SHALL remain linked to the source template

