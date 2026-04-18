-- v2.2 Cluster A2 — dashboard_summary 键值聚合建表

CREATE TABLE IF NOT EXISTS dashboard_summary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_key VARCHAR(100) NOT NULL UNIQUE,
    metric_value TEXT,
    refreshed_at DATETIME NOT NULL DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_summary_metric_key
    ON dashboard_summary (metric_key);
