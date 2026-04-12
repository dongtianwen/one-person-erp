import sqlite3

def fix_db_more():
    conn = sqlite3.connect("backend/shubiao.db")
    cursor = conn.cursor()
    
    # Create work_hour_logs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS work_hour_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            log_date TEXT NOT NULL,
            hours_spent REAL NOT NULL,
            task_description TEXT NOT NULL,
            deviation_note TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
        )
    """)
    print("Table work_hour_logs created.")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    fix_db_more()
