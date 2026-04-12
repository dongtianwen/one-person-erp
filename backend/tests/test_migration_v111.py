"""v1.11 迁移测试——覆盖表存在性、字段存在性、索引、唯一约束、旧数据不变。"""
import os
import sqlite3
import tempfile

import pytest

from migrations.v1_11_migrate import migrate, NEW_TABLES, ALL_INDEXES


def _setup_base_db(db_path: str) -> None:
    """创建基础 schema（模拟 v1.0 ~ v1.10 已有表）+ 插入样例行。"""
    c = sqlite3.connect(db_path)
    c.executescript("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(200) NOT NULL
        );
        CREATE TABLE IF NOT EXISTS acceptances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            result VARCHAR(20) NOT NULL,
            notes TEXT NULL
        );
        CREATE TABLE IF NOT EXISTS deliverables (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            deliverable_type VARCHAR(30) NOT NULL,
            notes TEXT NULL
        );
        CREATE TABLE IF NOT EXISTS requirements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            version_no VARCHAR(20) NOT NULL,
            summary TEXT NULL
        );
        INSERT INTO projects (name) VALUES ('旧项目');
        INSERT INTO acceptances (project_id, result) VALUES (1, 'passed');
        INSERT INTO deliverables (project_id, deliverable_type) VALUES (1, 'source_code');
        INSERT INTO requirements (project_id, version_no) VALUES (1, 'v1');
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


# ── NFR-1101 ──────────────────────────────────────────────────────


def test_all_new_tables_exist(conn):
    """验证 8 张新表全部创建。"""
    cur = conn.cursor()
    for table_name in NEW_TABLES:
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,),
        )
        assert cur.fetchone() is not None, f"{table_name} 表不存在"


def test_dataset_versions_has_metadata_fields(conn):
    """验证 dataset_versions 包含 data_source / label_schema_version / change_summary。"""
    cur = conn.cursor()
    columns = _column_info(cur, "dataset_versions")
    for field in ("data_source", "label_schema_version", "change_summary"):
        assert field in columns, f"dataset_versions.{field} 不存在"


def test_acceptances_delivery_package_id_exists(conn):
    """验证 acceptances.delivery_package_id 列存在。"""
    cur = conn.cursor()
    columns = _column_info(cur, "acceptances")
    assert "delivery_package_id" in columns


def test_acceptances_acceptance_type_exists(conn):
    """验证 acceptances.acceptance_type 列存在。"""
    cur = conn.cursor()
    columns = _column_info(cur, "acceptances")
    assert "acceptance_type" in columns


def test_deliverables_delivery_package_id_exists(conn):
    """验证 deliverables.delivery_package_id 列存在。"""
    cur = conn.cursor()
    columns = _column_info(cur, "deliverables")
    assert "delivery_package_id" in columns


def test_requirements_annotation_task_id_exists(conn):
    """验证 requirements.annotation_task_id 列存在。"""
    cur = conn.cursor()
    columns = _column_info(cur, "requirements")
    assert "annotation_task_id" in columns


def test_all_indexes_exist(conn):
    """验证 15 个索引全部创建。"""
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='index'")
    existing = {row[0] for row in cur.fetchall()}
    expected = {idx[0] for idx in ALL_INDEXES}
    missing = expected - existing
    assert not missing, f"索引缺失: {missing}"


def test_dataset_version_unique_constraint(conn):
    """验证 dataset_versions 的 (dataset_id, version_no) 唯一约束。"""
    cur = conn.cursor()
    cur.execute("INSERT INTO datasets (project_id, name) VALUES (1, 'DS1')")
    ds_id = cur.execute("SELECT last_insert_rowid()").fetchone()[0]
    cur.execute(
        "INSERT INTO dataset_versions (dataset_id, version_no) VALUES (?, 'v1.0')",
        (ds_id,),
    )
    conn.commit()
    with pytest.raises(sqlite3.IntegrityError):
        cur.execute(
            "INSERT INTO dataset_versions (dataset_id, version_no) VALUES (?, 'v1.0')",
            (ds_id,),
        )


def test_model_version_unique_constraint(conn):
    """验证 model_versions 的 (project_id, name, version_no) 唯一约束。"""
    cur = conn.cursor()
    cur.execute("INSERT INTO training_experiments (project_id, name) VALUES (1, 'EXP1')")
    exp_id = cur.execute("SELECT last_insert_rowid()").fetchone()[0]
    cur.execute(
        "INSERT INTO model_versions (project_id, experiment_id, name, version_no) VALUES (1, ?, 'M1', 'v1.0.0')",
        (exp_id,),
    )
    conn.commit()
    with pytest.raises(sqlite3.IntegrityError):
        cur.execute(
            "INSERT INTO model_versions (project_id, experiment_id, name, version_no) VALUES (1, ?, 'M1', 'v1.0.0')",
            (exp_id,),
        )


def test_existing_row_counts_unchanged(conn):
    """验证迁移后原有表行数不变。"""
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM projects")
    assert cur.fetchone()[0] == 1
    cur.execute("SELECT COUNT(*) FROM acceptances")
    assert cur.fetchone()[0] == 1


def test_existing_records_fields_unchanged(conn):
    """验证迁移后原有记录字段值不变。"""
    cur = conn.cursor()
    cur.execute("SELECT name FROM projects WHERE id = 1")
    assert cur.fetchone()[0] == "旧项目"
    cur.execute("SELECT result FROM acceptances WHERE id = 1")
    assert cur.fetchone()[0] == "passed"
    cur.execute("SELECT deliverable_type FROM deliverables WHERE id = 1")
    assert cur.fetchone()[0] == "source_code"
    cur.execute("SELECT version_no FROM requirements WHERE id = 1")
    assert cur.fetchone()[0] == "v1"
