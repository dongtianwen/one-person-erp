"""v2.0 数据库迁移测试——验证 5 张新表创建成功。"""
import sqlite3
import os
import pytest

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "shubiao.db")


@pytest.fixture(scope="module")
def db():
    """获取真实数据库连接（用于验证迁移）。"""
    conn = sqlite3.connect(DB_PATH)
    yield conn
    conn.close()


# Note: Uses conftest.py's db_session fixture for in-memory SQLite tests
# and the local db fixture for real database migration verification


class TestMigrationV200NewTables:
    """测试 v2.0 迁移创建的新表。"""

    def test_agent_runs_exists(self, db):
        """agent_runs 表应存在。"""
        cur = db.cursor()
        cur.execute("SELECT COUNT(*) FROM agent_runs")
        cur.fetchone()  # 不抛异常即存在

    def test_agent_suggestions_exists(self, db):
        """agent_suggestions 表应存在。"""
        cur = db.cursor()
        cur.execute("SELECT COUNT(*) FROM agent_suggestions")
        cur.fetchone()

    def test_agent_actions_exists(self, db):
        """agent_actions 表应存在。"""
        cur = db.cursor()
        cur.execute("SELECT COUNT(*) FROM agent_actions")
        cur.fetchone()

    def test_human_confirmations_exists(self, db):
        """human_confirmations 表应存在。"""
        cur = db.cursor()
        cur.execute("SELECT COUNT(*) FROM human_confirmations")
        cur.fetchone()

    def test_todos_exists(self, db):
        """todos 表应存在。"""
        cur = db.cursor()
        cur.execute("SELECT COUNT(*) FROM todos")
        cur.fetchone()


class TestMigrationV200Indexes:
    """测试 v2.0 迁移创建的新索引。"""

    def test_agent_runs_agent_type_index(self, db):
        """agent_runs 表应有 agent_type 索引。"""
        cur = db.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='agent_runs'")
        names = [row[0] for row in cur.fetchall()]
        assert any("agent_type" in n for n in names), f"缺少 agent_type 索引: {names}"

    def test_agent_runs_status_index(self, db):
        """agent_runs 表应有 status 索引。"""
        cur = db.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='agent_runs'")
        names = [row[0] for row in cur.fetchall()]
        assert any("status" in n for n in names), f"缺少 status 索引: {names}"

    def test_agent_suggestions_status_index(self, db):
        """agent_suggestions 表应有 status 索引。"""
        cur = db.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='agent_suggestions'")
        names = [row[0] for row in cur.fetchall()]
        assert any("status" in n for n in names), f"缺少 status 索引: {names}"


class TestMigrationV200Columns:
    """测试 v2.0 迁移创建的表字段。"""

    def test_agent_runs_columns(self, db):
        """agent_runs 表应包含必要字段。"""
        cur = db.cursor()
        cur.execute("PRAGMA table_info(agent_runs)")
        columns = {row[1] for row in cur.fetchall()}
        required = {"id", "agent_type", "trigger_type", "status", "llm_provider",
                     "llm_enhanced", "llm_model", "rule_output", "context_snapshot",
                     "error_message", "created_at", "updated_at", "is_deleted", "completed_at"}
        missing = required - columns
        assert not missing, f"agent_runs 缺少字段: {missing}"

    def test_agent_suggestions_columns(self, db):
        """agent_suggestions 表应包含必要字段。"""
        cur = db.cursor()
        cur.execute("PRAGMA table_info(agent_suggestions)")
        columns = {row[1] for row in cur.fetchall()}
        required = {"id", "agent_run_id", "decision_type", "suggestion_type", "title",
                     "description", "priority", "status", "suggested_action", "action_params",
                     "source_rule", "llm_enhanced", "created_at", "updated_at", "is_deleted"}
        missing = required - columns
        assert not missing, f"agent_suggestions 缺少字段: {missing}"

    def test_agent_actions_columns(self, db):
        """agent_actions 表应包含必要字段。"""
        cur = db.cursor()
        cur.execute("PRAGMA table_info(agent_actions)")
        columns = {row[1] for row in cur.fetchall()}
        required = {"id", "suggestion_id", "action_type", "action_params", "status",
                     "result", "error_message", "executed_at", "created_at", "updated_at", "is_deleted"}
        missing = required - columns
        assert not missing, f"agent_actions 缺少字段: {missing}"

    def test_human_confirmations_columns(self, db):
        """human_confirmations 表应包含必要字段。"""
        cur = db.cursor()
        cur.execute("PRAGMA table_info(human_confirmations)")
        columns = {row[1] for row in cur.fetchall()}
        required = {"id", "suggestion_id", "decision_type", "reason_code", "free_text_reason",
                     "corrected_fields", "user_priority_override", "inject_to_next_run",
                     "next_review_at", "created_at", "updated_at", "is_deleted"}
        missing = required - columns
        assert not missing, f"human_confirmations 缺少字段: {missing}"

    def test_todos_columns(self, db):
        """todos 表应包含必要字段。"""
        cur = db.cursor()
        cur.execute("PRAGMA table_info(todos)")
        columns = {row[1] for row in cur.fetchall()}
        required = {"id", "title", "description", "priority", "status", "due_date",
                     "is_completed", "source", "source_id", "created_at", "updated_at", "is_deleted"}
        missing = required - columns
        assert not missing, f"todos 缺少字段: {missing}"


class TestMigrationV200NoRegression:
    """测试 v2.0 迁移不影响原有表。"""

    def test_existing_tables_not_affected(self, db):
        """原有表应仍然可访问。"""
        tables = ["projects", "contracts", "finance_records", "milestones",
                  "tasks", "quotations", "fixed_costs", "reminders", "users"]
        cur = db.cursor()
        for table in tables:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            cur.fetchone()  # 不抛异常即正常

    def test_new_tables_do_not_interfere(self, db):
        """新表不应破坏原有查询。"""
        cur = db.cursor()
        cur.execute("SELECT COUNT(*) FROM projects")
        cur.fetchone()
