import sqlite3

def check_schema():
    conn = sqlite3.connect("backend/shubiao.db")
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(requirements)")
    columns = cursor.fetchall()
    for col in columns:
        print(col)
    conn.close()

if __name__ == "__main__":
    check_schema()
