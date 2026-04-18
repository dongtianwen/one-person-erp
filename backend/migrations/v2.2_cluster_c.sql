-- v2.2 Cluster C — meeting_minutes 建表 + 模板类型扩展

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
