"""v1.7 数据库迁移——项目执行控制模块。

扩展 change_orders、milestones、projects 表字段，新增 work_hour_logs 表，建立索引。

使用方法：
    cd backend
    python -m migrations.v1_7_migrate
"""
import sqlite3
import sys
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "shubiao.db")


def _column_exists(cur, table_name: str, column_name: str) -> bool:
    """检查表中是否存在指定列。"""
    cur.execute(f"PRAGMA table_info({table_name})")
    columns = {col[1] for col in cur.fetchall()}
    return column_name in columns


def _add_column_if_not_exists(cur, table: str, column: str, definition: str) -> bool:
    """如果列不存在则添加，返回是否执行了添加操作。"""
    if not _column_exists(cur, table, column):
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        print(f"  {table}.{column} 已添加")
        return True
    else:
        print(f"  {table}.{column} 已存在，跳过")
        return False


def migrate(db_path: str = DB_PATH) -> None:
    """执行 v1.7 迁移：扩展表 + 新表 + 索引。"""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    try:
        # ── 步骤 1：记录迁移前快照 ──────────────────────────────
        snapshot = {}
        for table in ["change_orders", "milestones", "projects"]:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            snapshot[table] = cur.fetchone()[0]
        print(f"迁移前快照: {snapshot}")

        # ── 步骤 2：扩展 change_orders 表 ─────────────────────
        print("\n扩展 change_orders 表:")
        _add_column_if_not_exists(
            cur, "change_orders", "status",
            "VARCHAR(20) NOT NULL DEFAULT 'pending'"
        )
        _add_column_if_not_exists(
            cur, "change_orders", "extra_days",
            "INTEGER NULL"
        )
        _add_column_if_not_exists(
            cur, "change_orders", "extra_amount",
            "DECIMAL(12,2) NULL"
        )
        _add_column_if_not_exists(
            cur, "change_orders", "client_confirmed_at",
            "TIMESTAMP NULL"
        )
        _add_column_if_not_exists(
            cur, "change_orders", "client_rejected_at",
            "TIMESTAMP NULL"
        )
        _add_column_if_not_exists(
            cur, "change_orders", "rejection_reason",
            "TEXT NULL"
        )

        # ── 步骤 3：扩展 milestones 表 ────────────────────────
        print("\n扩展 milestones 表:")
        _add_column_if_not_exists(
            cur, "milestones", "payment_amount",
            "DECIMAL(12,2) NULL"
        )
        _add_column_if_not_exists(
            cur, "milestones", "payment_due_date",
            "DATE NULL"
        )
        _add_column_if_not_exists(
            cur, "milestones", "payment_received_at",
            "TIMESTAMP NULL"
        )
        _add_column_if_not_exists(
            cur, "milestones", "payment_status",
            "VARCHAR(20) NOT NULL DEFAULT 'unpaid'"
        )

        # ── 步骤 4：扩展 projects 表 ─────────────────────────
        print("\n扩展 projects 表:")
        _add_column_if_not_exists(
            cur, "projects", "close_checklist",
            "TEXT NULL"
        )
        _add_column_if_not_exists(
            cur, "projects", "closed_at",
            "TIMESTAMP NULL"
        )
        _add_column_if_not_exists(
            cur, "projects", "estimated_hours",
            "INTEGER NULL"
        )
        _add_column_if_not_exists(
            cur, "projects", "actual_hours",
            "INTEGER NULL"
        )

        # ── 步骤 5：创建 work_hour_logs 表 ───────────────────
        print("\n创建 work_hour_logs 表:")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS work_hour_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                log_date DATE NOT NULL,
                hours_spent DECIMAL(6,2) NOT NULL,
                task_description TEXT NOT NULL,
                deviation_note TEXT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("  work_hour_logs 表已创建")

        # ── 步骤 6：创建索引 ──────────────────────────────────
        print("\n创建索引:")
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_change_orders_status ON change_orders(status)",
            "CREATE INDEX IF NOT EXISTS idx_milestones_payment_status ON milestones(payment_status)",
            "CREATE INDEX IF NOT EXISTS idx_work_hour_logs_project_id ON work_hour_logs(project_id)",
            "CREATE INDEX IF NOT EXISTS idx_work_hour_logs_log_date ON work_hour_logs(log_date)",
        ]
        for idx_sql in indexes:
            cur.execute(idx_sql)
            print(f"  {idx_sql.split('idx_')[1].split(' ')[0]} 索引已创建")

        # ── 步骤 7：迁移后验证 ─────────────────────────────────
        print("\n验证迁移结果:")

        # 验证原有数据行数未变
        for table, expected in snapshot.items():
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            actual = cur.fetchone()[0]
            assert actual == expected, \
                f"{table} 行数变化: 迁移前={expected}, 迁移后={actual}"
            print(f"  {table} 行数: {actual} (未变化)")

        # 验证新表存在
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='work_hour_logs'"
        )
        assert cur.fetchone() is not None, "work_hour_logs 表不存在"
        print("  work_hour_logs 表存在")

        # 验证新字段存在
        new_fields = {
            "change_orders": ["status", "extra_days", "extra_amount",
                           "client_confirmed_at", "client_rejected_at", "rejection_reason"],
            "milestones": ["payment_amount", "payment_due_date",
                          "payment_received_at", "payment_status"],
            "projects": ["close_checklist", "closed_at", "estimated_hours", "actual_hours"],
        }
        for table, fields in new_fields.items():
            cur.execute(f"PRAGMA table_info({table})")
            existing_columns = {col[1] for col in cur.fetchall()}
            for field in fields:
                assert field in existing_columns, f"{table}.{field} 不存在"
            print(f"  {table} 新字段全部存在")

        # 验证索引存在
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND "
            "name IN ('idx_change_orders_status', 'idx_milestones_payment_status', "
            "'idx_work_hour_logs_project_id', 'idx_work_hour_logs_log_date')"
        )
        idx_names = {row[0] for row in cur.fetchall()}
        expected_indexes = {
            "idx_change_orders_status",
            "idx_milestones_payment_status",
            "idx_work_hour_logs_project_id",
            "idx_work_hour_logs_log_date",
        }
        assert idx_names == expected_indexes, f"索引缺失: {expected_indexes - idx_names}"
        print("  所有索引已创建")

        conn.commit()
        print("\nv1.7 迁移完成：4 张表扩展 + 1 张新表 + 4 个索引")

    except Exception as e:
        conn.rollback()
        print(f"迁移失败: {e}", file=sys.stderr)
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
