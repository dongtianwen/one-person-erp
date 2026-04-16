## ADDED Requirements

### Requirement: System stores templates for document generation
The system SHALL store Jinja2 templates for quotation and contract generation in a dedicated templates table.

#### Scenario: Template table structure
- **WHEN** database schema is created
- **THEN** templates table SHALL exist with columns: id, name, template_type, content, is_default, description, created_at, updated_at

#### Scenario: Default templates
- **WHEN** system initializes
- **THEN** two default templates SHALL exist: one for quotation, one for contract
- **THEN** each template SHALL have template_type = 'quotation' or 'contract'
- **THEN** each template SHALL have is_default = 1
- **THEN** each template SHALL have unique constraint on (template_type, is_default) WHERE is_default = 1

#### Scenario: Non-default templates
- **WHEN** user creates a custom template
- **THEN** template SHALL have is_default = 0
- **THEN** template_id SHALL be a non-nullable integer in quotations and contracts tables

### Requirement: System provides template CRUD API
The system SHALL provide REST API endpoints for template management.

#### Scenario: List all templates
- **WHEN** client requests GET /api/v1/templates
- **THEN** system SHALL return list of all templates with name, template_type, is_default, description

#### Scenario: Create new template
- **WHEN** client requests POST /api/v1/templates with valid template data
- **THEN** system SHALL create template with template_type in whitelist ["quotation", "contract"]
- **THEN** system SHALL return created template with id

#### Scenario: Update existing template
- **WHEN** client requests PUT /api/v1/templates/{id} with valid template data
- **THEN** system SHALL update template name, content, description
- **THEN** system SHALL update updated_at timestamp

#### Scenario: Delete non-default template
- **WHEN** client requests DELETE /api/v1/templates/{id} for non-default template
- **THEN** system SHALL delete template
- **THEN** existing records with template_id = {id} SHALL keep generated_content (template_id becomes NULL)

#### Scenario: Delete default template
- **WHEN** client requests DELETE /api/v1/templates/{id} for default template
- **THEN** system SHALL reject with error TEMPLATE_IS_DEFAULT

#### Scenario: Validate template syntax on save
- **WHEN** client saves template with invalid Jinja2 syntax
- **THEN** system SHALL reject with error TEMPLATE_RENDER_FAILED
- **THEN** syntax error SHALL include error details for debugging

### Requirement: System supports setting default template
The system SHALL allow setting one template as default per template type.

#### Scenario: Set default template
- **WHEN** client requests PATCH /api/v1/templates/set-default with template_id and template_type
- **THEN** system SHALL atomically update old default template's is_default to 0
- **THEN** system SHALL update new template's is_default to 1
- **THEN** system SHALL ensure unique constraint is maintained

#### Scenario: Cannot set non-existent template as default
- **WHEN** client requests PATCH /api/v1/templates/set-default with non-existent template_id
- **THEN** system SHALL reject with error TEMPLATE_NOT_FOUND

#### Scenario: Cannot set non-whitelisted template type
- **WHEN** client requests PATCH /api/v1/templates/set-default with template_type not in whitelist
- **THEN** system SHALL reject with error TEMPLATE_NOT_FOUND

### Requirement: System provides default template retrieval API
The system SHALL provide endpoint to retrieve the current default template for a given type.

#### Scenario: Get default quotation template
- **WHEN** client requests GET /api/v1/templates/default/quotation
- **THEN** system SHALL return default quotation template with template_type = 'quotation' and is_default = 1
- **THEN** system SHALL throw TEMPLATE_NOT_FOUND if no default template exists

#### Scenario: Get default contract template
- **WHEN** client requests GET /api/v1/templates/default/contract
- **THEN** system SHALL return default contract template with template_type = 'contract' and is_default = 1
- **THEN** system SHALL throw TEMPLATE_NOT_FOUND if no default template exists

### Requirement: System enforces template variable consistency
The system SHALL define and enforce required and optional template variables for each template type.

#### Scenario: Quotation required variables
- **WHEN** rendering quotation template
- **THEN** system SHALL require all variables in QUOTATION_REQUIRED_VARS: quotation_no, customer_name, project_name, requirement_summary, estimate_days, total_amount, valid_until, created_date
- **THEN** system SHALL accept all variables in QUOTATION_OPTIONAL_VARS (missing values use empty string)

#### Scenario: Contract required variables
- **WHEN** rendering contract template
- **THEN** system SHALL require all variables in CONTRACT_REQUIRED_VARS: contract_no, customer_name, project_name, total_amount, sign_date, company_name, quotation_no
- **THEN** system SHALL accept all variables in CONTRACT_OPTIONAL_VARS (missing values use empty string)

### Requirement: System validates template variable alignment
The system SHALL verify that templates use only defined variables.

#### Scenario: Quotation template uses only defined variables
- **WHEN** checking quotation template content
- **THEN** system SHALL extract all {{ variable }} placeholders
- **THEN** system SHALL ensure all variables exist in QUOTATION_REQUIRED_VARS + QUOTATION_OPTIONAL_VARS

#### Scenario: Contract template uses only defined variables
- **WHEN** checking contract template content
- **THEN** system SHALL extract all {{ variable }} placeholders
- **THEN** system SHALL ensure all variables exist in CONTRACT_REQUIRED_VARS + CONTRACT_OPTIONAL_VARS
