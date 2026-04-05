# file-versioning Specification

## Purpose
文件索引版本管理，支持文件多版本追踪和分组显示。

## Requirements

### Requirement: File index entries SHALL have a file_group_id for version grouping

Each file index entry SHALL have a `file_group_id` field (UUID4 string, max 36 characters) that groups all versions of the same logical file. When a new file is created, the system SHALL automatically generate a new UUID4 as its `file_group_id`. When a new version is added to an existing file, the system SHALL reuse the parent file's `file_group_id`.

#### Scenario: New file gets auto-generated group ID
- **WHEN** user creates a new file index entry
- **THEN** system generates a new UUID4 and assigns it to `file_group_id`

#### Scenario: New version inherits parent group ID
- **WHEN** user adds a new version to an existing file
- **THEN** the new version receives the same `file_group_id` as the original file

### Requirement: Creating a new version SHALL demote the current version

When a new version is created for a file, the system SHALL automatically set `is_current = false` for all other entries in the same `file_group_id` that currently have `is_current = true`. The new version SHALL be marked as `is_current = true`.

#### Scenario: Demoting old version when creating new one
- **WHEN** user creates version "v2" for a file that has "v1" as current
- **THEN** "v1" `is_current` becomes false and "v2" `is_current` becomes true

### Requirement: File list SHALL group entries by file_group_id

The file index list endpoint SHALL return entries grouped by `file_group_id`. By default, only the current version (`is_current = true`) of each group SHALL be displayed. Users SHALL be able to expand a group to view all historical versions.

#### Scenario: Default list shows only current versions
- **WHEN** user views the file index list without expanding
- **THEN** only entries with `is_current = true` are shown, one per group

#### Scenario: Expanded view shows all versions
- **WHEN** user expands a file group
- **THEN** all versions sharing the same `file_group_id` are displayed, sorted by creation date descending

### Requirement: Deleting a file index entry SHALL delete only that version

Deleting a file index entry SHALL remove only that specific version. Other versions in the same `file_group_id` SHALL remain unaffected. If the deleted version was the only one in its group, the group is effectively removed.

#### Scenario: Delete one version keeps others
- **WHEN** user deletes version "v1" of a file that also has "v2"
- **THEN** "v2" remains in the system with its `file_group_id` unchanged
