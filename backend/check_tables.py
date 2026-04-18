import sqlite3, os
db_path = "erp.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [r[0] for r in cur.fetchall()]
    print("Tables:", tables)
    print("Has entity_snapshots:", "entity_snapshots" in tables)
    print("Has meeting_minutes:", "meeting_minutes" in tables)
    print("Has dashboard_summary:", "dashboard_summary" in tables)
    print("Has tool_entries:", "tool_entries" in tables)
    print("Has leads:", "leads" in tables)
    conn.close()
else:
    print("DB not found at", db_path)
