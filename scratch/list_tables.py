import sqlite3

def list_tables():
    conn = sqlite3.connect("backend/shubiao.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    for table in tables:
        print(table)
    conn.close()

if __name__ == "__main__":
    list_tables()
