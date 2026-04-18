-- v2.2 Cluster A1 — entity_snapshots 统一快照建表

CREATE TABLE IF NOT EXISTS entity_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type VARCHAR(50) NOT NULL,
    entity_id INTEGER NOT NULL,
    version_no INTEGER NOT NULL DEFAULT 1,
    snapshot_json TEXT NOT NULL,
    parent_snapshot_id INTEGER,
    is_latest BOOLEAN NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_snapshots_entity
    ON entity_snapshots (entity_type, entity_id, created_at);

CREATE INDEX IF NOT EXISTS idx_snapshots_latest
    ON entity_snapshots (entity_type, entity_id, is_latest);
