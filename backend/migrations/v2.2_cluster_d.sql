-- v2.2 Cluster D — tool_entries + leads 建表

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
