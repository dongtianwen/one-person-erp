import sqlite3

def fix_db():
    conn = sqlite3.connect("backend/shubiao.db")
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE requirements ADD COLUMN requirement_type VARCHAR(30)")
        print("Column requirement_type added to requirements.")
    except Exception as e:
        print(f"Error adding column: {e}")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    fix_db()
