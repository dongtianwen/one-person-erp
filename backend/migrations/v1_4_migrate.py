"""v1.4 数据库迁移——为 finance_records 新增 related_project_id 字段。

使用方法：
    cd backend
    python -m migrations.v1_4_migrate
"""
import sqlite3
import sys
import os

# 数据库路径（与 config.py 中 DATABASE_URL 对应）
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "shubiao.db")


def migrate(db_path: str = DB_PATH) -> None:
    """执行 v1.4 迁移：新增 related_project_id 字段及索引。"""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    try:
        # 检查字段是否已存在
        cur.execute("PRAGMA table_info('finance_records')")
        existing_cols = {row[1] for row in cur.fetchall()}

        if "related_project_id" not in existing_cols:
            cur.execute(
                "ALTER TABLE finance_records ADD COLUMN related_project_id INTEGER NULL "
                "REFERENCES projects(id) ON DELETE SET NULL"
            )
            print("已添加 related_project_id 字段")
        else:
            print("related_project_id 字段已存在，跳过")

        # 创建索引
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_finance_records_related_project_id "
            "ON finance_records(related_project_id)"
        )
        print("索引 idx_finance_records_related_project_id 已确保存在")

        conn.commit()
        print("v1.4 迁移完成")

    except Exception as e:
        conn.rollback()
        print(f"迁移失败: {e}", file=sys.stderr)
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
