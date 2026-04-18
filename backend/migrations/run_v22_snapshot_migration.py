"""Execute v2.2 dashboard snapshot migration against shubiao.db"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "shubiao.db")

def migrate():
    print(f"Database: {DB_PATH}")
    print(f"  exists: {os.path.exists(DB_PATH)}, size: {os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0} bytes")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables_before = [r[0] for r in cur.fetchall()]
    print(f"\nTables BEFORE ({len(tables_before)}): {tables_before}")

    scripts = {
        "A1-entity_snapshots": """
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
CREATE INDEX IF NOT EXISTS idx_snapshots_entity ON entity_snapshots (entity_type, entity_id, created_at);
CREATE INDEX IF NOT EXISTS idx_snapshots_latest ON entity_snapshots (entity_type, entity_id, is_latest);
        """,
        "A2-dashboard_summary": """
CREATE TABLE IF NOT EXISTS dashboard_summary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_key VARCHAR(100) NOT NULL UNIQUE,
    metric_value TEXT,
    refreshed_at DATETIME NOT NULL DEFAULT (datetime('now'))
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_summary_metric_key ON dashboard_summary (metric_key);
        """,
        "C-meeting_minutes": """
CREATE TABLE IF NOT EXISTS meeting_minutes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(200) NOT NULL,
    participants TEXT,
    conclusions TEXT,
    action_items TEXT,
    risk_points TEXT,
    project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL,
    client_id INTEGER REFERENCES customers(id) ON DELETE SET NULL,
    meeting_date DATETIME,
    created_at DATETIME NOT NULL DEFAULT (datetime('now')),
    updated_at DATETIME NOT NULL DEFAULT (datetime('now'))
);
        """,
        "D-tool_entries_leads": """
CREATE TABLE IF NOT EXISTS tool_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action_name VARCHAR(200) NOT NULL,
    tool_name VARCHAR(200) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    is_backfilled BOOLEAN NOT NULL DEFAULT 0,
    notes TEXT,
    created_at DATETIME NOT NULL DEFAULT (datetime('now')),
    updated_at DATETIME NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source VARCHAR(50) NOT NULL DEFAULT 'other',
    status VARCHAR(50) NOT NULL DEFAULT 'initial_contact',
    next_action VARCHAR(500),
    client_id INTEGER REFERENCES customers(id) ON DELETE SET NULL,
    project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL,
    notes TEXT,
    created_at DATETIME NOT NULL DEFAULT (datetime('now')),
    updated_at DATETIME NOT NULL DEFAULT (datetime('now'))
);
        """,
    }

    for name, sql in scripts.items():
        try:
            cur.executescript(sql)
            print(f"  Cluster {name}: DONE")
        except Exception as e:
            print(f"  Cluster {name}: ERROR - {e}")

    conn.commit()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables_after = [r[0] for r in cur.fetchall()]
    new_tables = set(tables_after) - set(tables_before)
    print(f"\nTables AFTER ({len(tables_after)}): {tables_after}")
    print(f"NEW tables: {new_tables}")

    v22_tables = ["entity_snapshots", "dashboard_summary", "meeting_minutes", "tool_entries", "leads"]
    for t in v22_tables:
        try:
            cur.execute(f"SELECT count(*) FROM [{t}]")
            count = cur.fetchone()[0]
            print(f"  {t}: {count} rows [OK]")
        except Exception as e:
            print(f"  {t}: ERROR - {e}")

    conn.close()
    print("\nMigration COMPLETE!")

if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        print(f"ERROR: Database not found: {DB_PATH}")
        import sys
        sys.exit(1)
    migrate()
