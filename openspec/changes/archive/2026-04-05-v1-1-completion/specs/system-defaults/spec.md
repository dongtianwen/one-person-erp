## ADDED Requirements

### Requirement: System SHALL have a settings table with system_initialized flag

The system SHALL maintain a `settings` table using a key-value design where each setting has a unique `key` (String) and a `value` (Text/JSON). The system SHALL check for a `system_initialized` key on startup. If absent or false, the system SHALL execute default template initialization. After successful initialization, the system SHALL set `system_initialized` to true.

#### Scenario: First startup triggers initialization
- **WHEN** system starts and `system_initialized` is not found or is false
- **THEN** system writes default reminder settings and default file indexes
- **AND** sets `system_initialized` to true in the settings table

#### Scenario: Subsequent startups skip initialization
- **WHEN** system starts and `system_initialized` is true
- **THEN** system skips default template initialization entirely

### Requirement: Default reminder settings SHALL be written on first initialization

On first initialization, the system SHALL write the following default reminder settings to the `reminder_settings` table:
- Annual audit reminder: March 31 every year
- Tax filing reminder: 15th of every month

#### Scenario: Default reminder settings are created
- **WHEN** system initializes for the first time
- **THEN** `reminder_settings` table contains annual audit and tax filing defaults
- **AND** both are marked as active

### Requirement: Default file indexes SHALL be written on first initialization

On first initialization, the system SHALL write the following default file index entries to the `file_indexes` table, each with a unique `file_group_id`:
- 营业执照正本 (business_license)
- 公司章程 (company_charter)
- 数标园入驻协议 (lease_agreement)
- 税务备案回执 (tax_registration)
- 首次审计报告 (audit_report)

#### Scenario: Default file indexes are created with group IDs
- **WHEN** system initializes for the first time
- **THEN** `file_indexes` table contains 5 default entries
- **AND** each entry has a unique `file_group_id`
- **AND** each entry has `is_current = true`

### Requirement: Users MAY edit or delete default templates after initialization

After initial seeding, users SHALL have full CRUD access to all default reminder settings and file index entries through the existing APIs. Deleting user-modified default entries SHALL follow the same rules as user-created entries.

#### Scenario: User deletes a default file index
- **WHEN** user deletes a seeded file index entry
- **THEN** the entry is soft-deleted following standard deletion rules
- **AND** system_initialized remains true
