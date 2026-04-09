"""v1.8 数据库迁移——财务对接模块。

新增 invoices 表、export_batches 表，扩展 finance_records 表字段，建立索引。

使用方法：
    cd backend
    python -m migrations.v1_8_migrate
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


def _table_exists(cur, table_name: str) -> bool:
    """检查表是否存在。"""
    cur.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
    return cur.fetchone() is not None


def _index_exists(cur, index_name: str) -> bool:
    """检查索引是否存在。"""
    cur.execute(f"SELECT name FROM sqlite_master WHERE type='index' AND name='{index_name}'")
    return cur.fetchone() is not None


def migrate(db_path: str = DB_PATH) -> None:
    """执行 v1.8 迁移：新表 + 扩展表 + 索引。"""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    try:
        # ── 步骤 1：记录迁移前快照 ──────────────────────────────
        snapshot = {}
        for table in ["finance_records", "contracts"]:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            snapshot[table] = cur.fetchone()[0]
        print(f"迁移前快照: {snapshot}")

        # ── 步骤 2：创建 invoices 表 ─────────────────────────
        print("\n创建 invoices 表:")
        if not _table_exists(cur, "invoices"):
            cur.execute("""
                CREATE TABLE invoices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    invoice_no VARCHAR(30) NOT NULL UNIQUE,
                    contract_id INTEGER NOT NULL REFERENCES contracts(id) ON DELETE RESTRICT,
                    invoice_type VARCHAR(20) NOT NULL DEFAULT 'standard',
                    invoice_date DATE NOT NULL,
                    amount_excluding_tax DECIMAL(12,2) NOT NULL,
                    tax_rate DECIMAL(5,4) NOT NULL DEFAULT 0.13,
                    tax_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
                    total_amount DECIMAL(12,2) NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'draft',
                    issued_at TIMESTAMP NULL,
                    received_at TIMESTAMP NULL,
                    received_by VARCHAR(100) NULL,
                    verified_at TIMESTAMP NULL,
                    notes TEXT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("  invoices 表已创建")
        else:
            print("  invoices 表已存在，跳过")

        # ── 步骤 3：创建 export_batches 表 ─────────────────────
        print("\n创建 export_batches 表:")
        if not _table_exists(cur, "export_batches"):
            cur.execute("""
                CREATE TABLE export_batches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    batch_id VARCHAR(50) NOT NULL UNIQUE,
                    export_type VARCHAR(30) NOT NULL,
                    target_format VARCHAR(20) NOT NULL DEFAULT 'generic',
                    accounting_period VARCHAR(7) NULL,
                    start_date DATE NOT NULL,
                    end_date DATE NOT NULL,
                    record_count INTEGER NOT NULL DEFAULT 0,
                    file_path TEXT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("  export_batches 表已创建")
        else:
            print("  export_batches 表已存在，跳过")

        # ── 步骤 4：扩展 finance_records 表 ───────────────────
        print("\n扩展 finance_records 表:")
        _add_column_if_not_exists(
            cur, "finance_records", "invoice_id",
            "INTEGER NULL REFERENCES invoices(id) ON DELETE SET NULL"
        )
        _add_column_if_not_exists(
            cur, "finance_records", "accounting_period",
            "VARCHAR(7) NULL"
        )
        _add_column_if_not_exists(
            cur, "finance_records", "export_batch_id",
            "VARCHAR(50) NULL"
        )
        _add_column_if_not_exists(
            cur, "finance_records", "reconciliation_status",
            "VARCHAR(20) NOT NULL DEFAULT 'pending'"
        )

        # ── 步骤 5：创建索引 ──────────────────────────────────
        print("\n创建索引:")

        # invoices 表索引
        invoices_indexes = [
            ("idx_invoices_contract_id", "CREATE INDEX IF NOT EXISTS idx_invoices_contract_id ON invoices(contract_id)"),
            ("idx_invoices_invoice_date", "CREATE INDEX IF NOT EXISTS idx_invoices_invoice_date ON invoices(invoice_date)"),
            ("idx_invoices_status", "CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status)"),
        ]

        # finance_records 表索引
        finance_indexes = [
            ("idx_finance_records_invoice_id", "CREATE INDEX IF NOT EXISTS idx_finance_records_invoice_id ON finance_records(invoice_id)"),
            ("idx_finance_records_accounting_period", "CREATE INDEX IF NOT EXISTS idx_finance_records_accounting_period ON finance_records(accounting_period)"),
            ("idx_finance_records_export_batch_id", "CREATE INDEX IF NOT EXISTS idx_finance_records_export_batch_id ON finance_records(export_batch_id)"),
            ("idx_finance_records_reconciliation_status", "CREATE INDEX IF NOT EXISTS idx_finance_records_reconciliation_status ON finance_records(reconciliation_status)"),
        ]

        # export_batches 表索引
        export_indexes = [
            ("idx_export_batches_accounting_period", "CREATE INDEX IF NOT EXISTS idx_export_batches_accounting_period ON export_batches(accounting_period)"),
            ("idx_export_batches_created_at", "CREATE INDEX IF NOT EXISTS idx_export_batches_created_at ON export_batches(created_at)"),
        ]

        all_indexes = invoices_indexes + finance_indexes + export_indexes
        for idx_name, idx_sql in all_indexes:
            if not _index_exists(cur, idx_name):
                cur.execute(idx_sql)
                print(f"  {idx_name} 索引已创建")
            else:
                print(f"  {idx_name} 索引已存在，跳过")

        # ── 步骤 6：迁移后验证 ─────────────────────────────────
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
            "SELECT name FROM sqlite_master WHERE type='table' AND name='invoices'"
        )
        assert cur.fetchone() is not None, "invoices 表不存在"
        print("  invoices 表存在")

        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='export_batches'"
        )
        assert cur.fetchone() is not None, "export_batches 表不存在"
        print("  export_batches 表存在")

        # 验证新字段存在
        new_fields = {
            "finance_records": ["invoice_id", "accounting_period", "export_batch_id", "reconciliation_status"],
        }
        for table, fields in new_fields.items():
            cur.execute(f"PRAGMA table_info({table})")
            existing_columns = {col[1] for col in cur.fetchall()}
            for field in fields:
                assert field in existing_columns, f"{table}.{field} 不存在"
            print(f"  {table} 新字段全部存在")

        # 验证索引存在
        expected_indexes = {idx[0] for idx in all_indexes}
        cur.execute("SELECT name FROM sqlite_master WHERE type='index'")
        existing_indexes = {row[0] for row in cur.fetchall()}
        missing_indexes = expected_indexes - existing_indexes
        assert not missing_indexes, f"索引缺失: {missing_indexes}"
        print(f"  所有 {len(expected_indexes)} 个索引已创建")

        # 验证外键约束
        cur.execute("PRAGMA foreign_key_list(invoices)")
        fk_list = cur.fetchall()
        assert any(fk[2] == 'contracts' for fk in fk_list), \
            "invoices.contract_id 外键约束缺失"
        print("  invoices.contract_id 外键约束存在")

        # 验证唯一约束
        cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='invoices'")
        create_sql = cur.fetchone()[0]
        assert 'invoice_no' in create_sql and 'UNIQUE' in create_sql, \
            "invoices.invoice_no 唯一约束缺失"
        print("  invoices.invoice_no 唯一约束存在")

        cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='export_batches'")
        create_sql = cur.fetchone()[0]
        assert 'batch_id' in create_sql and 'UNIQUE' in create_sql, \
            "export_batches.batch_id 唯一约束缺失"
        print("  export_batches.batch_id 唯一约束存在")

        # 验证默认值
        cur.execute(f"PRAGMA table_info(finance_records)")
        columns = {col[1]: col for col in cur.fetchall()}
        # PRAGMA table_info returns default value with quotes: "'pending'"
        default_val = columns['reconciliation_status'][4]
        assert default_val in ['pending', "'pending'"], \
            f"finance_records.reconciliation_status 默认值应为 'pending', 实际为 {default_val}"
        print("  finance_records.reconciliation_status 默认值为 'pending'")

        conn.commit()
        print("\nv1.8 迁移完成：2 张新表 + 1 张表扩展 + 10 个索引")

    except Exception as e:
        conn.rollback()
        print(f"迁移失败: {e}", file=sys.stderr)
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
