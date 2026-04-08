"""v1.6 数据库迁移——创建报价单相关新表、补齐合同反查字段、建立索引和外键约束。

使用方法：
    cd backend
    python -m migrations.v1_6_migrate
"""
import sqlite3
import sys
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "shubiao.db")


def _needs_rebuild(cur) -> bool:
    """检查旧 quotations 表是否需要重建（旧 schema 没有 quote_no 列）。"""
    cur.execute("PRAGMA table_info(quotations)")
    columns = {col[1] for col in cur.fetchall()}
    return "quote_no" not in columns


def _rebuild_quotations(conn, cur) -> None:
    """重建旧 quotations 表以适配 v1.6 schema，保留已有数据。"""
    # 1. 重命名旧表
    cur.execute("ALTER TABLE quotations RENAME TO quotations_old")

    # 2. 创建新表
    cur.execute("""
        CREATE TABLE quotations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quote_no VARCHAR(30) NOT NULL UNIQUE,
            customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
            project_id INTEGER NULL REFERENCES projects(id) ON DELETE SET NULL,
            title VARCHAR(200) NOT NULL,
            requirement_summary TEXT NOT NULL,
            estimate_days INTEGER NOT NULL,
            estimate_hours INTEGER NULL,
            daily_rate DECIMAL(12,2) NULL,
            direct_cost DECIMAL(12,2) NULL,
            risk_buffer_rate DECIMAL(5,2) NOT NULL DEFAULT 0,
            discount_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
            tax_rate DECIMAL(5,4) NOT NULL DEFAULT 0,
            subtotal_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
            tax_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
            total_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
            valid_until DATE NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'draft',
            notes TEXT NULL,
            sent_at TIMESTAMP NULL,
            accepted_at TIMESTAMP NULL,
            rejected_at TIMESTAMP NULL,
            expired_at TIMESTAMP NULL,
            converted_contract_id INTEGER NULL REFERENCES contracts(id) ON DELETE SET NULL,
            is_deleted BOOLEAN NOT NULL DEFAULT 0,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 3. 迁移数据：旧字段 → 新字段
    cur.execute("""
        INSERT INTO quotations (
            id, quote_no, customer_id, title, requirement_summary,
            estimate_days, total_amount, subtotal_amount, valid_until,
            status, notes, converted_contract_id,
            is_deleted, created_at, updated_at
        )
        SELECT
            id,
            quotation_number,
            customer_id,
            title,
            COALESCE(content, ''),
            30,
            amount,
            amount,
            validity_date,
            status,
            discount_note,
            contract_id,
            is_deleted,
            created_at,
            updated_at
        FROM quotations_old
    """)

    # 4. 删除旧表
    cur.execute("DROP TABLE quotations_old")
    print(f"  quotations 表已重建，迁移了 {cur.rowcount} 条记录")


def migrate(db_path: str = DB_PATH) -> None:
    """执行 v1.6 迁移：创建报价单三张表 + 合同反查字段 + 全部索引。"""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    try:
        # ── 步骤 1：记录迁移前快照 ──────────────────────────────
        snapshot = {}
        for table in ["customers", "projects", "contracts"]:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            snapshot[table] = cur.fetchone()[0]
        print(f"迁移前快照: {snapshot}")

        # ── 步骤 2：处理 quotations 表 ─────────────────────────
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='quotations'"
        )
        quotations_exists = cur.fetchone() is not None

        if quotations_exists and _needs_rebuild(cur):
            print("  检测到旧版 quotations 表，开始重建...")
            _rebuild_quotations(conn, cur)
        elif not quotations_exists:
            cur.execute("""
                CREATE TABLE quotations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    quote_no VARCHAR(30) NOT NULL UNIQUE,
                    customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
                    project_id INTEGER NULL REFERENCES projects(id) ON DELETE SET NULL,
                    title VARCHAR(200) NOT NULL,
                    requirement_summary TEXT NOT NULL,
                    estimate_days INTEGER NOT NULL,
                    estimate_hours INTEGER NULL,
                    daily_rate DECIMAL(12,2) NULL,
                    direct_cost DECIMAL(12,2) NULL,
                    risk_buffer_rate DECIMAL(5,2) NOT NULL DEFAULT 0,
                    discount_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
                    tax_rate DECIMAL(5,4) NOT NULL DEFAULT 0,
                    subtotal_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
                    tax_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
                    total_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
                    valid_until DATE NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'draft',
                    notes TEXT NULL,
                    sent_at TIMESTAMP NULL,
                    accepted_at TIMESTAMP NULL,
                    rejected_at TIMESTAMP NULL,
                    expired_at TIMESTAMP NULL,
                    converted_contract_id INTEGER NULL REFERENCES contracts(id) ON DELETE SET NULL,
                    is_deleted BOOLEAN NOT NULL DEFAULT 0,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("  quotations 表已创建")

        # ── 步骤 3：创建 quotation_items 表 ────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS quotation_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quotation_id INTEGER NOT NULL REFERENCES quotations(id) ON DELETE CASCADE,
                item_name VARCHAR(200) NOT NULL,
                item_type VARCHAR(20) NOT NULL,
                quantity DECIMAL(12,2) NOT NULL DEFAULT 1,
                unit_price DECIMAL(12,2) NOT NULL DEFAULT 0,
                amount DECIMAL(12,2) NOT NULL DEFAULT 0,
                notes TEXT NULL,
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ── 步骤 4：创建 quotation_changes 表 ──────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS quotation_changes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quotation_id INTEGER NOT NULL REFERENCES quotations(id) ON DELETE CASCADE,
                change_type VARCHAR(20) NOT NULL,
                before_snapshot TEXT NOT NULL,
                after_snapshot TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ── 步骤 5：contracts 表补充 quotation_id ──────────────
        cur.execute("PRAGMA table_info(contracts)")
        columns = [col[1] for col in cur.fetchall()]
        if "quotation_id" not in columns:
            cur.execute(
                "ALTER TABLE contracts ADD COLUMN quotation_id INTEGER NULL "
                "REFERENCES quotations(id) ON DELETE SET NULL"
            )
            # 回填：从已转合同的报价单同步 quotation_id
            cur.execute("""
                UPDATE contracts SET quotation_id = (
                    SELECT q.id FROM quotations q
                    WHERE q.converted_contract_id = contracts.id
                )
                WHERE EXISTS (
                    SELECT 1 FROM quotations q
                    WHERE q.converted_contract_id = contracts.id
                )
            """)

        # ── 步骤 6：创建索引 ──────────────────────────────────
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_quotations_customer_id ON quotations(customer_id)",
            "CREATE INDEX IF NOT EXISTS idx_quotations_project_id ON quotations(project_id)",
            "CREATE INDEX IF NOT EXISTS idx_quotations_status ON quotations(status)",
            "CREATE INDEX IF NOT EXISTS idx_quotations_valid_until ON quotations(valid_until)",
            "CREATE INDEX IF NOT EXISTS idx_quotation_items_quotation_id ON quotation_items(quotation_id)",
            "CREATE INDEX IF NOT EXISTS idx_quotation_items_sort_order ON quotation_items(sort_order)",
            "CREATE INDEX IF NOT EXISTS idx_quotation_changes_quotation_id ON quotation_changes(quotation_id)",
            "CREATE INDEX IF NOT EXISTS idx_contracts_quotation_id ON contracts(quotation_id)",
        ]
        for idx_sql in indexes:
            cur.execute(idx_sql)

        # ── 步骤 7：迁移后验证 ─────────────────────────────────
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name IN ('quotations','quotation_items','quotation_changes')"
        )
        new_tables = {row[0] for row in cur.fetchall()}
        expected_tables = {"quotations", "quotation_items", "quotation_changes"}
        assert new_tables == expected_tables, \
            f"缺少新表: {expected_tables - new_tables}"

        for table, expected in snapshot.items():
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            actual = cur.fetchone()[0]
            assert actual == expected, \
                f"{table} 行数变化: 迁移前={expected}, 迁移后={actual}"

        cur.execute("PRAGMA table_info(contracts)")
        col_names = [col[1] for col in cur.fetchall()]
        assert "quotation_id" in col_names, "contracts.quotation_id 不存在"

        # 验证索引
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND ("
            "name LIKE 'idx_quotation%' OR name = 'idx_contracts_quotation_id'"
            ")"
        )
        idx_names = {row[0] for row in cur.fetchall()}
        assert len(idx_names) >= 8, f"索引不足: {idx_names}"

        conn.commit()
        print("v1.6 迁移完成：3 张新表 + 8 个索引 + contracts.quotation_id 已创建")

    except Exception as e:
        conn.rollback()
        print(f"迁移失败: {e}", file=sys.stderr)
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
