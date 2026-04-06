## ADDED Requirements

### Requirement: v1.3 database migration for contracts and finance_records
The system SHALL provide migration script `backend/migrations/v1_3_migrate.py` that adds 2 fields to contracts (expected_payment_date, payment_stage_note) and 7 fields to finance_records (outsource_name, has_invoice, tax_treatment, invoice_direction, invoice_type, tax_rate, tax_amount). Three indexes SHALL be created: idx_contracts_expected_payment_date, idx_finance_records_invoice_direction, idx_finance_records_invoice_no. All new fields default to NULL. Migration MUST preserve all existing data.

#### Scenario: Migration preserves row counts
- **WHEN** migration is executed
- **THEN** finance_records and contracts row counts are unchanged

#### Scenario: Migration preserves existing field values
- **WHEN** migration is executed
- **THEN** randomly sampled records have identical field values to pre-migration snapshot

#### Scenario: New fields default to NULL
- **WHEN** migration is executed on existing records
- **THEN** all new fields have NULL value for every existing row

#### Scenario: All three indexes exist after migration
- **WHEN** migration is executed
- **THEN** PRAGMA index_list confirms all three indexes exist
