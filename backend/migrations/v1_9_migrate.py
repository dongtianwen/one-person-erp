"""v1.9 数据库迁移脚本 - 风险控制与成本视图模块。

新增：
- fixed_costs 表：固定成本登记
- input_invoices 表：进项发票记录
扩展：
- customers 表：逾期统计和风险等级字段
- projects 表：粗利润缓存字段
"""

import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent.parent / "shubiao.db"


def get_table_info(conn, table_name):
    """获取表结构信息。"""
    cursor = conn.execute(f"PRAGMA table_info({table_name})")
    return {row[1]: row for row in cursor.fetchall()}


def get_row_count(conn, table_name):
    """获取表行数。"""
    cursor = conn.execute(f"SELECT COUNT(*) FROM {table_name}")
    return cursor.fetchone()[0]


def get_sample_records(conn, table_name, columns, limit=3):
    """获取抽样记录。"""
    cursor = conn.execute(
        f"SELECT {', '.join(columns)} FROM {table_name} ORDER BY id LIMIT ?",
        (limit,)
    )
    return cursor.fetchall()


def record_snapshot(conn):
    """迁移前记录快照。"""
    snapshot = {
        "timestamp": datetime.now().isoformat(),
        "tables": {}
    }
    
    # 记录主要表的行数
    for table in ["projects", "customers", "milestones", "contracts", "finance_records"]:
        try:
            count = get_row_count(conn, table)
            snapshot["tables"][table] = {"row_count": count}
            print(f"✓ {table}: {count} 行")
        except sqlite3.OperationalError:
            print(f"✗ {table}: 表不存在")
    
    # 抽样记录
    for table in ["projects", "customers", "contracts"]:
        try:
            columns = ["id", "name"] if table != "contracts" else ["id", "contract_no"]
            samples = get_sample_records(conn, table, columns)
            snapshot["tables"][table]["samples"] = samples
            print(f"  {table} 抽样：{samples[:2]}")
        except Exception as e:
            print(f"  {table} 抽样失败：{e}")
    
    return snapshot


def add_column_if_not_exists(conn, table_name, column_name, column_def):
    """如果字段不存在则添加。"""
    table_info = get_table_info(conn, table_name)
    if column_name not in table_info:
        sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}"
        conn.execute(sql)
        print(f"✓ {table_name}.{column_name} 已添加")
    else:
        print(f"⊘ {table_name}.{column_name} 已存在