# db-migrations Specification

## Purpose
数据库迁移管理，使用 Alembic 进行版本控制的 schema 变更。

## Requirements

### Requirement: Database schema changes SHALL be managed through Alembic migrations

All database schema changes SHALL be implemented as Alembic migration scripts. The project SHALL use `alembic` for version-controlled schema migrations instead of `Base.metadata.create_all()`.

#### Scenario: Running migrations applies schema changes
- **WHEN** developer runs `alembic upgrade head`
- **THEN** all pending migrations are applied in order
- **AND** the database schema matches the current code expectations

#### Scenario: Migration history is tracked
- **WHEN** a new migration is generated
- **THEN** a migration file is created in `backend/alembic/versions/`
- **AND** the `alembic_version` table is updated with the new revision

### Requirement: Existing data SHALL be preserved during migrations

All migration scripts SHALL preserve existing data. New columns SHALL have appropriate default values for existing rows. The migration for `file_group_id` SHALL backfill UUIDs for existing records grouped by `(file_name, file_type)`.

#### Scenario: Adding settlement_status preserves existing records
- **WHEN** migration adds `settlement_status` to `finance_records`
- **THEN** existing records have `settlement_status` set to NULL
- **AND** no existing data is lost or modified

#### Scenario: Backfilling file_group_id groups existing records
- **WHEN** migration adds `file_group_id` to existing `file_indexes`
- **THEN** records with the same `(file_name, file_type)` receive the same UUID
- **AND** all existing records retain their original data

### Requirement: Settings table SHALL be created via migration

The `settings` table SHALL be created as a new table through an Alembic migration, not through `create_all()`. The migration SHALL create the table with columns: `key` (String, unique, primary key), `value` (Text), `created_at` (DateTime), `updated_at` (DateTime).

#### Scenario: Settings table is created by migration
- **WHEN** migration for settings table runs
- **THEN** `settings` table exists with key, value, created_at, updated_at columns
- **AND** `key` column has a unique constraint

### Requirement: Application startup SHALL run pending migrations automatically

On application startup, the system SHALL check for and apply any pending Alembic migrations before serving requests. This SHALL happen in the FastAPI lifespan event. If migration fails, the application SHALL log the error and exit.

#### Scenario: Auto-migration on startup succeeds
- **WHEN** application starts with pending migrations
- **THEN** migrations are applied automatically
- **AND** application continues normally

#### Scenario: Migration failure prevents startup
- **WHEN** migration fails during startup
- **THEN** application logs the error
- **AND** application exits with non-zero status code
