"""v1.12 迁移测试——覆盖表存在性、字段存在性、索引、唯一约束、默认模板插入、幂等性。"""
import os
import sqlite3
import tempfile

import pytest

from migrations.v1_12_migrate import migrate


def _setup_base_db(db_path: str) -> None:
    """创建基础 schema（模拟 v1.0 ~ v1.11 已有表）+ 插入样例行。"""
    c = sqlite3.connect(db_path)
    c.executescript("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(200) NOT NULL
        );
        CREATE TABLE IF NOT EXISTS quotations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'draft'
        );
        CREATE TABLE IF NOT EXISTS contracts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quotation_id INTEGER NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'draft'
        );
        INSERT INTO projects (name) VALUES ('旧项目');
        INSERT INTO quotations (project_id, status) VALUES (1, 'draft');
        INSERT INTO contracts (quotation_id, status) VALUES (1, 'draft');
    """)
    c.commit()
    c.close()


@pytest.fixture
def db_path():
    """创建临时文件数据库用于测试。"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    _setup_base_db(path)
    yield path
    os.unlink(path)


@pytest.fixture
def conn(db_path):
    """返回已迁移的数据库连接。"""
    migrate(db_path)
    c = sqlite3.connect(db_path)
    yield c
    c.close()


def _column_info(cur, table: str) -> set[str]:
    cur.execute(f"PRAGMA table_info({table})")
    return {col[1] for col in cur.fetchall()}


# ── Task 1.12: templates table existence ──────────────────────────


def test_templates_table_exists(conn):
    """验证 templates 表已创建。"""
    cur = conn.cursor()
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='templates'"
    )
    assert cur.fetchone() is not None, "templates 表不存在"


def test_templates_table_columns(conn):
    """验证 templates 表包含所有预期列。"""
    cur = conn.cursor()
    columns = _column_info(cur, "templates")
    expected_columns = {
        "id", "name", "template_type", "content",
        "is_default", "description", "created_at", "updated_at"
    }
    missing = expected_columns - columns
    assert not missing, f"templates 表缺失列: {missing}"


# ── Task 1.13: quotations new columns ─────────────────────────────


def test_quotations_new_columns_exist(conn):
    """验证 quotations 表新增字段全部存在。"""
    cur = conn.cursor()
    columns = _column_info(cur, "quotations")
    for field in ("generated_content", "template_id", "content_generated_at"):
        assert field in columns, f"quotations.{field} 不存在"


# ── Task 1.14: contracts new columns ──────────────────────────────


def test_contracts_new_columns_exist(conn):
    """验证 contracts 表新增字段全部存在。"""
    cur = conn.cursor()
    columns = _column_info(cur, "contracts")
    for field in ("generated_content", "template_id", "content_generated_at"):
        assert field in columns, f"contracts.{field} 不存在"


# ── Task 1.15: default templates insertion (idempotent) ───────────


def test_default_templates_inserted(conn):
    """验证默认模板已插入。"""
    cur = conn.cursor()
    cur.execute("SELECT id, name, template_type FROM templates WHERE is_default = 1")
    templates = cur.fetchall()
    assert len(templates) == 2, f"默认模板数量应为 2，实际为 {len(templates)}"

    types = {t[1] for t in templates}
    assert "默认报价模板" in types, "默认报价模板未插入"
    assert "默认合同模板" in types, "默认合同模板未插入"


def test_default_templates_idempotent(db_path):
    """验证迁移幂等性：重复执行不重复插入。"""
    migrate(db_path)
    migrate(db_path)

    c = sqlite3.connect(db_path)
    cur = c.cursor()
    cur.execute("SELECT COUNT(*) FROM templates WHERE is_default = 1")
    count = cur.fetchone()[0]
    c.close()

    assert count == 2, f"重复迁移后默认模板数量应为 2，实际为 {count}"


# ── Task 1.16: unique constraint on default templates ─────────────


def test_unique_constraint_default_quotation(conn):
    """验证报价单默认模板的唯一约束。"""
    cur = conn.cursor()
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_templates_default_quotation'"
    )
    assert cur.fetchone() is not None, "idx_templates_default_quotation 索引不存在"


def test_unique_constraint_default_contract(conn):
    """验证合同默认模板的唯一约束。"""
    cur = conn.cursor()
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_templates_default_contract'"
    )
    assert cur.fetchone() is not None, "idx_templates_default_contract 索引不存在"


def test_only_one_default_per_type(conn):
    """验证每种模板类型只有一个默认模板。"""
    cur = conn.cursor()
    cur.execute(
        "SELECT template_type, COUNT(*) as cnt FROM templates WHERE is_default = 1 GROUP BY template_type HAVING cnt > 1"
    )
    duplicates = cur.fetchall()
    assert not duplicates, f"存在多个默认模板的类型: {duplicates}"


# ── Task 1.17: migration idempotency ──────────────────────────────


def test_migration_idempotent(db_path):
    """验证迁移可以安全地重复执行。"""
    # 第一次迁移
    migrate(db_path)

    c1 = sqlite3.connect(db_path)
    cur1 = c1.cursor()
    cur1.execute("SELECT COUNT(*) FROM templates")
    count1 = cur1.fetchone()[0]
    c1.close()

    # 第二次迁移
    migrate(db_path)

    c2 = sqlite3.connect(db_path)
    cur2 = c2.cursor()
    cur2.execute("SELECT COUNT(*) FROM templates")
    count2 = cur2.fetchone()[0]
    cur2.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='templates'")
    table_exists = cur2.fetchone() is not None
    c2.close()

    assert table_exists, "templates 表在第二次迁移后不存在"
    assert count1 == count2, f"迁移幂等性 violation: 第一次 {count1} 条, 第二次 {count2} 条"


def test_migration_preserves_existing_data(db_path):
    """验证迁移不破坏原有数据。"""
    # 插入样例行
    c = sqlite3.connect(db_path)
    c.execute("INSERT INTO quotations (project_id, status) VALUES (1, 'sent')")
    c.execute("INSERT INTO contracts (quotation_id, status) VALUES (1, 'active')")
    c.commit()
    c.close()

    # 执行迁移
    migrate(db_path)

    # 验证原有数据仍然存在
    c = sqlite3.connect(db_path)
    cur = c.cursor()
    cur.execute("SELECT COUNT(*) FROM quotations")
    quotation_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM contracts")
    contract_count = cur.fetchone()[0]
    c.close()

    assert quotation_count >= 2, f"quotations 数据丢失: 预期 >= 2 条，实际 {quotation_count} 条"
    assert contract_count >= 2, f"contracts 数据丢失: 预期 >= 2 条，实际 {contract_count} 条"
