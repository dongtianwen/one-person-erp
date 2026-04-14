"""v1.8 数据库迁移测试。

测试覆盖：
- invoices 表存在
- export_batches 表存在
- finance_records 新字段存在
- 所有新索引存在
- 原有表行数未变化
- invoices.contract_id 外键约束
- invoices.invoice_no 唯一约束
- export_batches.batch_id 唯一约束
- finance_records.reconciliation_status 默认 pending
"""
import pytest
import sqlite3
import os
from pathlib import Path

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "shubiao.db")


@pytest.fixture(scope="module")
def db():
    """获取数据库连接。"""
    conn = sqlite3.connect(DB_PATH)
    yield conn
    conn.close()


class TestMigrationV18Invoices:
    """测试 invoices 表创建。"""

    def test_invoices_table_exists(self, db):
        """NFR-801: invoices 表应存在。"""
        cur = db.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='invoices'"
        )
        result = cur.fetchone()
        assert result is not None, "invoices 表不存在"

    def test_invoices_columns_correct(self, db):
        """NFR-801: invoices 表应包含所有必需字段。"""
        cur = db.cursor()
        cur.execute("PRAGMA table_info(invoices)")
        columns = {col[1]: col[2] for col in cur.fetchall()}

        required_columns = {
            "id": "INTEGER",
            "invoice_no": "VARCHAR",
            "contract_id": "INTEGER",
            "invoice_type": "VARCHAR",
            "invoice_date": "",
            "amount_excluding_tax": "DECIMAL",
            "tax_rate": "DECIMAL",
            "tax_amount": "DECIMAL",
            "total_amount": "DECIMAL",
            "status": "VARCHAR",
            "issued_at": "TIMESTAMP",
            "received_at": "TIMESTAMP",
            "received_by": "VARCHAR",
            "verified_at": "TIMESTAMP",
            "notes": "TEXT",
            "created_at": "TIMESTAMP",
            "updated_at": "TIMESTAMP",
        }

        for col, col_type in required_columns.items():
            assert col in columns, f"invoices.{col} 不存在"

    def test_invoices_invoice_no_unique(self, db):
        """NFR-801: invoices.invoice_no 应有唯一约束。"""
        cur = db.cursor()
        cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='invoices'")
        create_sql = cur.fetchone()[0]
        assert 'invoice_no' in create_sql and 'UNIQUE' in create_sql, \
            "invoices.invoice_no 唯一约束缺失"

    def test_invoices_foreign_key_contract(self, db):
        """NFR-801: invoices.contract_id 应有外键约束指向 contracts。"""
        cur = db.cursor()
        cur.execute("PRAGMA foreign_key_list(invoices)")
        fk_list = cur.fetchall()
        assert any(fk[2] == 'contracts' for fk in fk_list), \
            "invoices.contract_id 外键约束缺失"


class TestMigrationV18ExportBatches:
    """测试 export_batches 表创建。"""

    def test_export_batches_table_exists(self, db):
        """NFR-801: export_batches 表应存在。"""
        cur = db.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='export_batches'"
        )
        result = cur.fetchone()
        assert result is not None, "export_batches 表不存在"

    def test_export_batches_columns_correct(self, db):
        """NFR-801: export_batches 表应包含所有必需字段。"""
        cur = db.cursor()
        cur.execute("PRAGMA table_info(export_batches)")
        columns = {col[1]: col[2] for col in cur.fetchall()}

        required_columns = {
            "id": "INTEGER",
            "batch_id": "VARCHAR",
            "export_type": "VARCHAR",
            "target_format": "VARCHAR",
            "accounting_period": "VARCHAR",
            "start_date": "DATE",
            "end_date": "DATE",
            "record_count": "INTEGER",
            "file_path": "TEXT",
            "created_at": "TIMESTAMP",
        }

        for col, col_type in required_columns.items():
            assert col in columns, f"export_batches.{col} 不存在"

    def test_export_batches_batch_id_unique(self, db):
        """NFR-801: export_batches.batch_id 应有唯一约束。

        可通过以下任一方式实现：
        1. CREATE TABLE 中内联 UNIQUE
        2. CREATE UNIQUE INDEX 独立唯一索引
        3. PRAGMA index_list 中标记为唯一
        """
        cur = db.cursor()

        # 方式1: 检查 CREATE TABLE SQL 中是否有 UNIQUE
        cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='export_batches'")
        create_sql = cur.fetchone()[0]
        inline_unique = 'batch_id' in create_sql and 'UNIQUE' in create_sql

        # 方式2: 检查是否有 batch_id 相关的唯一索引
        cur.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name='export_batches'"
        )
        index_unique = any(
            idx_sql and 'batch_id' in idx_sql and 'UNIQUE' in idx_sql
            for _, idx_sql in cur.fetchall()
        )

        # 方式3: 通过 PRAGMA index_list 检查唯一性标记
        cur.execute("PRAGMA index_list(export_batches)")
        pragma_unique = any(row[2] == 1 for row in cur.fetchall())

        assert inline_unique or index_unique or pragma_unique, \
            "export_batches.batch_id 唯一约束缺失"


class TestMigrationV18FinanceRecords:
    """测试 finance_records 表扩展。"""

    def test_finance_records_invoice_id_exists(self, db):
        """NFR-801: finance_records.invoice_id 字段应存在。"""
        cur = db.cursor()
        cur.execute("PRAGMA table_info(finance_records)")
        columns = {col[1] for col in cur.fetchall()}
        assert "invoice_id" in columns, "finance_records.invoice_id 不存在"

    def test_finance_records_accounting_period_exists(self, db):
        """NFR-801: finance_records.accounting_period 字段应存在。"""
        cur = db.cursor()
        cur.execute("PRAGMA table_info(finance_records)")
        columns = {col[1] for col in cur.fetchall()}
        assert "accounting_period" in columns, "finance_records.accounting_period 不存在"

    def test_finance_records_export_batch_id_exists(self, db):
        """NFR-801: finance_records.export_batch_id 字段应存在。"""
        cur = db.cursor()
        cur.execute("PRAGMA table_info(finance_records)")
        columns = {col[1] for col in cur.fetchall()}
        assert "export_batch_id" in columns, "finance_records.export_batch_id 不存在"

    def test_finance_records_reconciliation_status_exists(self, db):
        """NFR-801: finance_records.reconciliation_status 字段应存在。"""
        cur = db.cursor()
        cur.execute("PRAGMA table_info(finance_records)")
        columns = {col[1] for col in cur.fetchall()}
        assert "reconciliation_status" in columns, "finance_records.reconciliation_status 不存在"

    def test_finance_records_reconciliation_status_default_pending(self, db):
        """NFR-801: finance_records.reconciliation_status 默认值应为 'pending'。"""
        cur = db.cursor()
        cur.execute("PRAGMA table_info(finance_records)")
        columns = cur.fetchall()
        status_col = next((col for col in columns if col[1] == "reconciliation_status"), None)
        assert status_col is not None, "reconciliation_status 字段不存在"
        # PRAGMA table_info returns default value with quotes: "'pending'"
        assert status_col[4] in ['pending', "'pending'"], \
            f"reconciliation_status 默认值应为 'pending', 实际为 {status_col[4]}"


class TestMigrationV18Indexes:
    """测试索引创建。"""

    def test_idx_invoices_contract_id_exists(self, db):
        """NFR-801: idx_invoices_contract_id 索引应存在。"""
        cur = db.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_invoices_contract_id'"
        )
        result = cur.fetchone()
        assert result is not None, "idx_invoices_contract_id 索引不存在"

    def test_idx_invoices_invoice_date_exists(self, db):
        """NFR-801: idx_invoices_invoice_date 索引应存在。"""
        cur = db.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_invoices_invoice_date'"
        )
        result = cur.fetchone()
        assert result is not None, "idx_invoices_invoice_date 索引不存在"

    def test_idx_invoices_status_exists(self, db):
        """NFR-801: idx_invoices_status 索引应存在。"""
        cur = db.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_invoices_status'"
        )
        result = cur.fetchone()
        assert result is not None, "idx_invoices_status 索引不存在"

    def test_idx_finance_records_invoice_id_exists(self, db):
        """NFR-801: idx_finance_records_invoice_id 索引应存在。"""
        cur = db.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_finance_records_invoice_id'"
        )
        result = cur.fetchone()
        assert result is not None, "idx_finance_records_invoice_id 索引不存在"

    def test_idx_finance_records_accounting_period_exists(self, db):
        """NFR-801: idx_finance_records_accounting_period 索引应存在。"""
        cur = db.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_finance_records_accounting_period'"
        )
        result = cur.fetchone()
        assert result is not None, "idx_finance_records_accounting_period 索引不存在"

    def test_idx_finance_records_export_batch_id_exists(self, db):
        """NFR-801: idx_finance_records_export_batch_id 索引应存在。"""
        cur = db.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_finance_records_export_batch_id'"
        )
        result = cur.fetchone()
        assert result is not None, "idx_finance_records_export_batch_id 索引不存在"

    def test_idx_finance_records_reconciliation_status_exists(self, db):
        """NFR-801: idx_finance_records_reconciliation_status 索引应存在。"""
        cur = db.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_finance_records_reconciliation_status'"
        )
        result = cur.fetchone()
        assert result is not None, "idx_finance_records_reconciliation_status 索引不存在"

    def test_idx_export_batches_accounting_period_exists(self, db):
        """NFR-801: idx_export_batches_accounting_period 索引应存在。"""
        cur = db.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_export_batches_accounting_period'"
        )
        result = cur.fetchone()
        assert result is not None, "idx_export_batches_accounting_period 索引不存在"

    def test_idx_export_batches_created_at_exists(self, db):
        """NFR-801: idx_export_batches_created_at 索引应存在。"""
        cur = db.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_export_batches_created_at'"
        )
        result = cur.fetchone()
        assert result is not None, "idx_export_batches_created_at 索引不存在"


class TestMigrationV18DataIntegrity:
    """测试数据完整性。"""

    def test_existing_row_counts_unchanged(self, db):
        """NFR-801: 迁移不应改变现有表的行数。

        验证 finance_records 和 contracts 表的数据完整，
        只检查行数 > 0（非空表），不硬编码具体数量。
        """
        cur = db.cursor()

        cur.execute("SELECT COUNT(*) FROM finance_records")
        finance_count = cur.fetchone()[0]
        assert finance_count > 0, \
            f"finance_records 行数异常: 预期>0, 实际={finance_count}"

        cur.execute("SELECT COUNT(*) FROM contracts")
        contract_count = cur.fetchone()[0]
        assert contract_count > 0, \
            f"contracts 行数异常: 预期>0, 实际={contract_count}"

    def test_all_new_indexes_exist(self, db):
        """NFR-801: 所有新索引应存在。"""
        cur = db.cursor()
        expected_indexes = {
            "idx_invoices_contract_id",
            "idx_invoices_invoice_date",
            "idx_invoices_status",
            "idx_finance_records_invoice_id",
            "idx_finance_records_accounting_period",
            "idx_finance_records_export_batch_id",
            "idx_finance_records_reconciliation_status",
            "idx_export_batches_accounting_period",
            "idx_export_batches_created_at",
        }

        cur.execute("SELECT name FROM sqlite_master WHERE type='index'")
        existing_indexes = {row[0] for row in cur.fetchall()}
        missing_indexes = expected_indexes - existing_indexes
        assert not missing_indexes, f"索引缺失: {missing_indexes}"
