"""v1.11 数据库迁移——数据标注与模型开发交付台账。

新增 8 张表：datasets / dataset_versions / annotation_tasks /
training_experiments / experiment_dataset_versions / model_versions /
delivery_packages / package_model_versions / package_dataset_versions，
扩展 3 张现有表（acceptances / deliverables / requirements），建立索引。

使用方法：
    cd backend
    python -m migrations.v1_11_migrate
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
    cur.execute(
        f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'"
    )
    return cur.fetchone() is not None


def _index_exists(cur, index_name: str) -> bool:
    """检查索引是否存在。"""
    cur.execute(
        f"SELECT name FROM sqlite_master WHERE type='index' AND name='{index_name}'"
    )
    return cur.fetchone() is not None


def _take_snapshot(cur) -> dict:
    """迁移前记录快照（行数 + 字段列表）。"""
    snapshot = {}
    tables = ["projects", "acceptances", "deliverables", "requirements"]
    for table in tables:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        cur.execute(f"PRAGMA table_info({table})")
        fields = [col[1] for col in cur.fetchall()]
        snapshot[table] = {"count": count, "fields": fields}
    return snapshot


# ── DDL 定义 ──────────────────────────────────────────────────────

NEW_TABLES = {
    "datasets": """
        CREATE TABLE IF NOT EXISTS datasets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
            name VARCHAR(200) NOT NULL,
            dataset_type VARCHAR(30) NOT NULL DEFAULT 'other',
            description TEXT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "dataset_versions": """
        CREATE TABLE IF NOT EXISTS dataset_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dataset_id INTEGER NOT NULL REFERENCES datasets(id) ON DELETE RESTRICT,
            version_no VARCHAR(20) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'draft',
            sample_count INTEGER NULL,
            file_path TEXT NULL,
            data_source TEXT NULL,
            label_schema_version VARCHAR(50) NULL,
            change_summary TEXT NULL,
            notes TEXT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(dataset_id, version_no)
        )
    """,
    "annotation_tasks": """
        CREATE TABLE IF NOT EXISTS annotation_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
            dataset_version_id INTEGER NOT NULL REFERENCES dataset_versions(id) ON DELETE RESTRICT,
            name VARCHAR(200) NOT NULL,
            status VARCHAR(30) NOT NULL DEFAULT 'pending',
            batch_no VARCHAR(50) NULL,
            sample_count INTEGER NULL,
            annotator_count INTEGER NULL,
            quality_check_result TEXT NULL,
            rework_reason TEXT NULL,
            completed_at TIMESTAMP NULL,
            notes TEXT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "training_experiments": """
        CREATE TABLE IF NOT EXISTS training_experiments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
            name VARCHAR(200) NOT NULL,
            description TEXT NULL,
            framework VARCHAR(100) NULL,
            hyperparameters TEXT NULL,
            metrics TEXT NULL,
            started_at TIMESTAMP NULL,
            finished_at TIMESTAMP NULL,
            notes TEXT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "experiment_dataset_versions": """
        CREATE TABLE IF NOT EXISTS experiment_dataset_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            experiment_id INTEGER NOT NULL REFERENCES training_experiments(id) ON DELETE CASCADE,
            dataset_version_id INTEGER NOT NULL REFERENCES dataset_versions(id) ON DELETE RESTRICT,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(experiment_id, dataset_version_id)
        )
    """,
    "model_versions": """
        CREATE TABLE IF NOT EXISTS model_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
            experiment_id INTEGER NOT NULL REFERENCES training_experiments(id) ON DELETE RESTRICT,
            name VARCHAR(200) NOT NULL,
            version_no VARCHAR(30) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'training',
            metrics TEXT NULL,
            file_path TEXT NULL,
            notes TEXT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(project_id, name, version_no)
        )
    """,
    "delivery_packages": """
        CREATE TABLE IF NOT EXISTS delivery_packages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
            name VARCHAR(200) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'draft',
            description TEXT NULL,
            delivered_at TIMESTAMP NULL,
            notes TEXT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "package_model_versions": """
        CREATE TABLE IF NOT EXISTS package_model_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            package_id INTEGER NOT NULL REFERENCES delivery_packages(id) ON DELETE CASCADE,
            model_version_id INTEGER NOT NULL REFERENCES model_versions(id) ON DELETE RESTRICT,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(package_id, model_version_id)
        )
    """,
    "package_dataset_versions": """
        CREATE TABLE IF NOT EXISTS package_dataset_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            package_id INTEGER NOT NULL REFERENCES delivery_packages(id) ON DELETE CASCADE,
            dataset_version_id INTEGER NOT NULL REFERENCES dataset_versions(id) ON DELETE RESTRICT,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(package_id, dataset_version_id)
        )
    """,
}

ALL_INDEXES = [
    ("idx_datasets_project_id",
     "CREATE INDEX IF NOT EXISTS idx_datasets_project_id ON datasets(project_id)"),
    ("idx_dataset_versions_dataset_id",
     "CREATE INDEX IF NOT EXISTS idx_dataset_versions_dataset_id ON dataset_versions(dataset_id)"),
    ("idx_dataset_versions_status",
     "CREATE INDEX IF NOT EXISTS idx_dataset_versions_status ON dataset_versions(status)"),
    ("idx_annotation_tasks_project_id",
     "CREATE INDEX IF NOT EXISTS idx_annotation_tasks_project_id ON annotation_tasks(project_id)"),
    ("idx_annotation_tasks_dataset_version_id",
     "CREATE INDEX IF NOT EXISTS idx_annotation_tasks_dataset_version_id ON annotation_tasks(dataset_version_id)"),
    ("idx_training_experiments_project_id",
     "CREATE INDEX IF NOT EXISTS idx_training_experiments_project_id ON training_experiments(project_id)"),
    ("idx_experiment_dataset_versions_experiment_id",
     "CREATE INDEX IF NOT EXISTS idx_experiment_dataset_versions_experiment_id ON experiment_dataset_versions(experiment_id)"),
    ("idx_experiment_dataset_versions_version_id",
     "CREATE INDEX IF NOT EXISTS idx_experiment_dataset_versions_version_id ON experiment_dataset_versions(dataset_version_id)"),
    ("idx_model_versions_project_id",
     "CREATE INDEX IF NOT EXISTS idx_model_versions_project_id ON model_versions(project_id)"),
    ("idx_model_versions_experiment_id",
     "CREATE INDEX IF NOT EXISTS idx_model_versions_experiment_id ON model_versions(experiment_id)"),
    ("idx_model_versions_status",
     "CREATE INDEX IF NOT EXISTS idx_model_versions_status ON model_versions(status)"),
    ("idx_delivery_packages_project_id",
     "CREATE INDEX IF NOT EXISTS idx_delivery_packages_project_id ON delivery_packages(project_id)"),
    ("idx_acceptances_delivery_package_id",
     "CREATE INDEX IF NOT EXISTS idx_acceptances_delivery_package_id ON acceptances(delivery_package_id)"),
    ("idx_deliverables_delivery_package_id",
     "CREATE INDEX IF NOT EXISTS idx_deliverables_delivery_package_id ON deliverables(delivery_package_id)"),
    ("idx_requirements_annotation_task_id",
     "CREATE INDEX IF NOT EXISTS idx_requirements_annotation_task_id ON requirements(annotation_task_id)"),
]


def migrate(db_path: str = DB_PATH) -> None:
    """执行 v1.11 迁移：8 张新表 + 3 张表扩展 + 15 个索引。"""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    try:
        # ── 步骤 1：记录迁移前快照 ──────────────────────────────
        print("步骤 1：记录迁移前快照")
        snapshot = _take_snapshot(cur)
        for table, info in snapshot.items():
            print(f"  {table}: {info['count']} 行, 字段={info['fields']}")

        # ── 步骤 2：创建新表 ────────────────────────────────────
        step = 2
        for table_name, ddl in NEW_TABLES.items():
            print(f"\n步骤 {step}：创建 {table_name} 表:")
            if not _table_exists(cur, table_name):
                cur.execute(ddl)
                print(f"  {table_name} 表已创建")
            else:
                print(f"  {table_name} 表已存在，跳过")
            step += 1

        # ── 步骤 11：扩展现有表 ─────────────────────────────────
        print(f"\n步骤 {step}：扩展现有表:")
        _add_column_if_not_exists(
            cur, "acceptances", "delivery_package_id",
            "INTEGER NULL REFERENCES delivery_packages(id) ON DELETE RESTRICT"
        )
        _add_column_if_not_exists(
            cur, "acceptances", "acceptance_type",
            "VARCHAR(20) NULL"
        )
        _add_column_if_not_exists(
            cur, "deliverables", "delivery_package_id",
            "INTEGER NULL REFERENCES delivery_packages(id) ON DELETE SET NULL"
        )
        _add_column_if_not_exists(
            cur, "requirements", "annotation_task_id",
            "INTEGER NULL REFERENCES annotation_tasks(id) ON DELETE SET NULL"
        )
        step += 1

        # ── 步骤 12：创建索引 ──────────────────────────────────
        print(f"\n步骤 {step}：创建索引:")
        for idx_name, idx_sql in ALL_INDEXES:
            if not _index_exists(cur, idx_name):
                cur.execute(idx_sql)
                print(f"  {idx_name} 索引已创建")
            else:
                print(f"  {idx_name} 索引已存在，跳过")
        step += 1

        # ── 步骤 13：迁移后验证 ─────────────────────────────────
        print(f"\n步骤 {step}：迁移后验证:")

        # 验证新表存在
        for table_name in NEW_TABLES:
            assert _table_exists(cur, table_name), f"{table_name} 表不存在"
            print(f"  {table_name} 表存在")

        # 验证 dataset_versions 元数据字段
        for field in ["data_source", "label_schema_version", "change_summary"]:
            assert _column_exists(cur, "dataset_versions", field), \
                f"dataset_versions.{field} 不存在"
        print("  dataset_versions 元数据字段全部存在")

        # 验证扩展表新字段
        for field in ["delivery_package_id", "acceptance_type"]:
            assert _column_exists(cur, "acceptances", field), \
                f"acceptances.{field} 不存在"
        assert _column_exists(cur, "deliverables", "delivery_package_id"), \
            "deliverables.delivery_package_id 不存在"
        assert _column_exists(cur, "requirements", "annotation_task_id"), \
            "requirements.annotation_task_id 不存在"
        print("  扩展表新字段全部存在")

        # 验证索引
        expected_indexes = {idx[0] for idx in ALL_INDEXES}
        cur.execute("SELECT name FROM sqlite_master WHERE type='index'")
        existing_indexes = {row[0] for row in cur.fetchall()}
        missing = expected_indexes - existing_indexes
        assert not missing, f"索引缺失: {missing}"
        print(f"  所有 {len(expected_indexes)} 个索引已创建")

        # 验证原有表行数一致
        for table, info in snapshot.items():
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            actual = cur.fetchone()[0]
            assert actual == info["count"], \
                f"{table} 行数变化: 迁移前={info['count']}, 迁移后={actual}"
            print(f"  {table} 行数: {actual} (未变化)")

        conn.commit()
        print(f"\nv1.11 迁移完成：{len(NEW_TABLES)} 张新表 + 3 张表扩展 + {len(ALL_INDEXES)} 个索引")

    except Exception as e:
        conn.rollback()
        print(f"迁移失败: {e}", file=sys.stderr)
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
