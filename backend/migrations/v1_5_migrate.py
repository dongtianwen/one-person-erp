"""v1.5 数据库迁移——创建需求管理、验收、交付物、版本发布、变更单、售后维护期相关表。

使用方法：
    cd backend
    python -m migrations.v1_5_migrate
"""
import sqlite3
import sys
import os

# 数据库路径（与 config.py 中 DATABASE_URL 对应）
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "shubiao.db")


def migrate(db_path: str = DB_PATH) -> None:
    """执行 v1.5 迁移：创建 8 张新表及全部索引和外键约束。"""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    try:
        # ── 需求版本表 ──────────────────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS requirements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                version_no VARCHAR(50) NOT NULL,
                summary TEXT NOT NULL,
                confirm_status VARCHAR(20) NOT NULL DEFAULT 'pending',
                confirmed_at TIMESTAMP NULL,
                confirm_method VARCHAR(20) NULL,
                is_current BOOLEAN NOT NULL DEFAULT FALSE,
                notes TEXT NULL,
                is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ── 变更单表（需先建，requirement_changes 有外键引用）────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS change_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_no VARCHAR(30) NOT NULL UNIQUE,
                contract_id INTEGER NOT NULL REFERENCES contracts(id) ON DELETE RESTRICT,
                requirement_change_id INTEGER NULL,
                title VARCHAR(200) NOT NULL,
                description TEXT NOT NULL,
                amount DECIMAL(12,2) NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'draft',
                confirmed_at TIMESTAMP NULL,
                confirm_method VARCHAR(20) NULL,
                notes TEXT NULL,
                is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ── 需求变更记录表 ─────────────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS requirement_changes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                requirement_id INTEGER NOT NULL REFERENCES requirements(id) ON DELETE CASCADE,
                title VARCHAR(200) NOT NULL,
                description TEXT NOT NULL,
                change_type VARCHAR(20) NOT NULL,
                is_billable BOOLEAN NOT NULL DEFAULT FALSE,
                change_order_id INTEGER NULL REFERENCES change_orders(id) ON DELETE SET NULL,
                initiated_by VARCHAR(20) NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ── 验收记录表 ─────────────────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS acceptances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
                milestone_id INTEGER NULL REFERENCES milestones(id) ON DELETE SET NULL,
                acceptance_name VARCHAR(200) NOT NULL,
                acceptance_date DATE NOT NULL,
                acceptor_name VARCHAR(100) NOT NULL,
                acceptor_title VARCHAR(100) NULL,
                result VARCHAR(20) NOT NULL,
                notes TEXT NULL,
                trigger_payment_reminder BOOLEAN NOT NULL DEFAULT FALSE,
                reminder_id INTEGER NULL REFERENCES reminders(id) ON DELETE SET NULL,
                confirm_method VARCHAR(20) NOT NULL,
                is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ── 交付物记录表 ───────────────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS deliverables (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
                acceptance_id INTEGER NULL REFERENCES acceptances(id) ON DELETE SET NULL,
                name VARCHAR(200) NOT NULL,
                deliverable_type VARCHAR(30) NOT NULL,
                delivery_date DATE NOT NULL,
                recipient_name VARCHAR(100) NOT NULL,
                delivery_method VARCHAR(20) NOT NULL,
                description TEXT NULL,
                storage_location VARCHAR(500) NULL,
                version_no VARCHAR(50) NULL,
                is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ── 账号交接条目表 ─────────────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS account_handovers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deliverable_id INTEGER NOT NULL REFERENCES deliverables(id) ON DELETE CASCADE,
                platform_name VARCHAR(200) NOT NULL,
                account_name VARCHAR(200) NOT NULL,
                notes VARCHAR(500) NULL
            )
        """)

        # ── 版本发布记录表 ─────────────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS releases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
                deliverable_id INTEGER NULL REFERENCES deliverables(id) ON DELETE SET NULL,
                version_no VARCHAR(50) NOT NULL,
                release_date DATE NOT NULL,
                release_type VARCHAR(20) NOT NULL,
                is_current_online BOOLEAN NOT NULL DEFAULT FALSE,
                changelog TEXT NOT NULL,
                deploy_env VARCHAR(20) NULL,
                notes TEXT NULL,
                is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ── 售后/维护期记录表 ─────────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS maintenance_periods (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
                contract_id INTEGER NULL REFERENCES contracts(id) ON DELETE SET NULL,
                service_type VARCHAR(20) NOT NULL,
                service_description VARCHAR(500) NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                annual_fee DECIMAL(10,2) NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'active',
                renewed_by_id INTEGER NULL REFERENCES maintenance_periods(id) ON DELETE SET NULL,
                notes TEXT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ── 核心索引 ──────────────────────────────────────────
        cur.execute("CREATE INDEX IF NOT EXISTS idx_requirements_project_id ON requirements(project_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_requirements_is_current ON requirements(is_current)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_requirement_changes_requirement_id ON requirement_changes(requirement_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_requirement_changes_change_order_id ON requirement_changes(change_order_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_acceptances_project_id ON acceptances(project_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_acceptances_acceptance_date ON acceptances(acceptance_date)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_acceptances_reminder_id ON acceptances(reminder_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_deliverables_project_id ON deliverables(project_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_deliverables_delivery_date ON deliverables(delivery_date)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_deliverables_acceptance_id ON deliverables(acceptance_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_releases_project_id ON releases(project_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_releases_is_current_online ON releases(is_current_online)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_releases_deliverable_id ON releases(deliverable_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_change_orders_contract_id ON change_orders(contract_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_change_orders_status ON change_orders(status)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_maintenance_periods_project_id ON maintenance_periods(project_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_maintenance_periods_end_date ON maintenance_periods(end_date)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_maintenance_periods_status ON maintenance_periods(status)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_maintenance_periods_renewed_by_id ON maintenance_periods(renewed_by_id)")

        conn.commit()
        print("v1.5 迁移完成：8 张新表 + 全部索引已创建")

    except Exception as e:
        conn.rollback()
        print(f"迁移失败: {e}", file=sys.stderr)
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
