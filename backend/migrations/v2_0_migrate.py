"""v2.0 AI Agent 闭环——Agent 核心表和待办表。

新增 5 张表：
- agent_runs: Agent 运行记录
- agent_suggestions: Agent 建议
- agent_actions: Agent 动作
- human_confirmations: 人工确认
- todos: 待办事项

使用方法：
    cd backend
    python -m migrations.v2_0_migrate
"""
import sqlite3
import sys
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "shubiao.db")


def _table_exists(cur, table_name: str) -> bool:
    """检查表是否存在。"""
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    )
    return cur.fetchone() is not None


def _create_table_if_not_exists(cur, table: str, definition: str) -> bool:
    """如果表不存在则创建，返回是否执行了创建操作。"""
    if not _table_exists(cur, table):
        cur.execute(definition)
        print(f"  {table} 已创建")
        return True
    else:
        print(f"  {table} 已存在，跳过")
        return False


def migrate():
    """执行 v2.0 数据库迁移。"""
    print("v2.0 数据库迁移开始...")
    print(f"数据库路径: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    try:
        # 1. agent_runs
        _create_table_if_not_exists(cur, "agent_runs", """
            CREATE TABLE agent_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_type VARCHAR(50) NOT NULL,
                trigger_type VARCHAR(20) NOT NULL DEFAULT 'manual',
                status VARCHAR(20) NOT NULL DEFAULT 'running',
                llm_provider VARCHAR(20),
                llm_enhanced INTEGER NOT NULL DEFAULT 0,
                llm_model VARCHAR(100),
                rule_output TEXT,
                context_snapshot JSON,
                error_message TEXT,
                created_at DATETIME NOT NULL DEFAULT (datetime('now')),
                updated_at DATETIME NOT NULL DEFAULT (datetime('now')),
                is_deleted INTEGER NOT NULL DEFAULT 0,
                completed_at DATETIME
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_agent_runs_agent_type ON agent_runs(agent_type)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_agent_runs_status ON agent_runs(status)")

        # 2. agent_suggestions
        _create_table_if_not_exists(cur, "agent_suggestions", """
            CREATE TABLE agent_suggestions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_run_id INTEGER NOT NULL,
                decision_type VARCHAR(50) NOT NULL,
                suggestion_type VARCHAR(50) NOT NULL,
                title VARCHAR(200) NOT NULL,
                description TEXT NOT NULL,
                priority VARCHAR(20) NOT NULL DEFAULT 'medium',
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                suggested_action VARCHAR(50) NOT NULL DEFAULT 'none',
                action_params TEXT,
                source_rule VARCHAR(100),
                llm_enhanced INTEGER NOT NULL DEFAULT 0,
                created_at DATETIME NOT NULL DEFAULT (datetime('now')),
                updated_at DATETIME NOT NULL DEFAULT (datetime('now')),
                is_deleted INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (agent_run_id) REFERENCES agent_runs(id)
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_agent_suggestions_run ON agent_suggestions(agent_run_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_agent_suggestions_status ON agent_suggestions(status)")

        # 3. agent_actions
        _create_table_if_not_exists(cur, "agent_actions", """
            CREATE TABLE agent_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                suggestion_id INTEGER NOT NULL,
                action_type VARCHAR(50) NOT NULL,
                action_params TEXT,
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                result TEXT,
                error_message TEXT,
                executed_at DATETIME,
                created_at DATETIME NOT NULL DEFAULT (datetime('now')),
                updated_at DATETIME NOT NULL DEFAULT (datetime('now')),
                is_deleted INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (suggestion_id) REFERENCES agent_suggestions(id)
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_agent_actions_suggestion ON agent_actions(suggestion_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_agent_actions_status ON agent_actions(status)")

        # 4. human_confirmations
        _create_table_if_not_exists(cur, "human_confirmations", """
            CREATE TABLE human_confirmations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                suggestion_id INTEGER NOT NULL,
                decision_type VARCHAR(20) NOT NULL,
                reason_code VARCHAR(50),
                free_text_reason TEXT,
                corrected_fields TEXT,
                user_priority_override VARCHAR(20),
                inject_to_next_run INTEGER NOT NULL DEFAULT 1,
                next_review_at DATETIME,
                created_at DATETIME NOT NULL DEFAULT (datetime('now')),
                updated_at DATETIME NOT NULL DEFAULT (datetime('now')),
                is_deleted INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (suggestion_id) REFERENCES agent_suggestions(id)
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_human_confirmations_suggestion ON human_confirmations(suggestion_id)")

        # 5. todos
        _create_table_if_not_exists(cur, "todos", """
            CREATE TABLE todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title VARCHAR(200) NOT NULL,
                description TEXT DEFAULT '',
                priority VARCHAR(20) DEFAULT 'medium',
                status VARCHAR(20) DEFAULT 'pending',
                due_date DATE,
                is_completed INTEGER NOT NULL DEFAULT 0,
                source VARCHAR(50),
                source_id INTEGER,
                created_at DATETIME NOT NULL DEFAULT (datetime('now')),
                updated_at DATETIME NOT NULL DEFAULT (datetime('now')),
                is_deleted INTEGER NOT NULL DEFAULT 0
            )
        """)

        conn.commit()
        print("\nv2.0 数据库迁移完成！")

    except Exception as e:
        conn.rollback()
        print(f"\n迁移失败: {e}", file=sys.stderr)
        conn.close()
        raise

    conn.close()


if __name__ == "__main__":
    migrate()
