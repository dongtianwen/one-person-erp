"""v2.2 Agent 决策智能体——风险评分与策略库迁移。

为 agent_suggestions 表新增 3 列：
- risk_score: INTEGER DEFAULT 0
- strategy_code: VARCHAR(50) DEFAULT ''
- score_breakdown: TEXT NULL

使用方法：
    cd backend
    python -m migrations.v2_2_migrate
"""
import sqlite3
import sys
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "shubiao.db")


def _column_exists(cur, table_name: str, col_name: str) -> bool:
    cur.execute(f"PRAGMA table_info({table_name})")
    return any(row[1] == col_name for row in cur.fetchall())


def migrate() -> dict:
    results = {}
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    new_columns = [
        ("risk_score", "INTEGER NOT NULL DEFAULT 0"),
        ("strategy_code", "VARCHAR(50) NOT NULL DEFAULT ''"),
        ("score_breakdown", "TEXT"),
    ]

    for col_name, col_def in new_columns:
        if _column_exists(cur, "agent_suggestions", col_name):
            results[col_name] = "already_exists"
            continue
        try:
            cur.execute(
                f"ALTER TABLE agent_suggestions ADD COLUMN {col_name} {col_def}"
            )
            results[col_name] = "added"
        except Exception as e:
            results[col_name] = f"error: {e}"

    conn.commit()
    conn.close()
    return results


if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        print(f"错误：数据库文件不存在: {DB_PATH}")
        sys.exit(1)
    print(f"开始迁移: {DB_PATH}")
    results = migrate()
    for col, status in results.items():
        print(f"  {col}: {status}")
    print("迁移完成")
