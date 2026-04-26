"""
调整待办事项数据以符合演示需求：
- 优先级分布：高/中/低都有
- 至少2条已逾期任务
- 在现有数据基础上修改
"""

import sqlite3
import os
from datetime import date, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "shubiao.db")

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. 查看当前待办任务（未完成的）
    cur.execute("""
        SELECT id, title, priority, status, due_date, project_id
        FROM tasks
        WHERE status IN ('todo', 'in_progress') AND is_deleted = 0
        ORDER BY due_date
    """)
    tasks = cur.fetchall()
    print("当前待办任务：")
    for t in tasks:
        print(f"  ID={t[0]}: {t[1]} | 优先级={t[2]} | 状态={t[3]} | 截止={t[4]} | 项目ID={t[5]}")

    # 2. 修改：数据集准备 → 低优先级（已有1条中优先级，改这条为低）
    cur.execute("""
        UPDATE tasks
        SET priority = 'low'
        WHERE title = '数据集准备' AND is_deleted = 0
    """)
    print(f"\n修改优先级：数据集准备 → low，影响 {cur.rowcount} 行")

    # 3. 修改：技术方案设计 → 截止日期改为已逾期（5天前）
    overdue_date = (date.today() - timedelta(days=5)).isoformat()
    cur.execute("""
        UPDATE tasks
        SET due_date = ?
        WHERE title = '技术方案设计' AND is_deleted = 0
    """, (overdue_date,))
    print(f"修改截止日期：技术方案设计 → {overdue_date}（已逾期），影响 {cur.rowcount} 行")

    # 4. 新增1条低优先级已逾期任务（挂到"政务数据标注平台"项目下）
    # 先找到该项目ID
    cur.execute("SELECT id FROM projects WHERE name = '政务数据标注平台' AND is_deleted = 0")
    row = cur.fetchone()
    if row:
        project_id = row[0]
        now = datetime.utcnow().isoformat()
        cur.execute("""
            INSERT INTO tasks (project_id, title, description, priority, status, assignee, due_date,
                             created_at, updated_at, is_deleted)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
        """, (project_id, "文档整理与归档", "项目文档整理、会议纪要归档、需求文档版本管理",
              "low", "todo", "张三", (date.today() - timedelta(days=3)).isoformat(),
              now, now))
        print(f"\n新增低优先级已逾期任务：文档整理与归档（截止={(date.today() - timedelta(days=3)).isoformat()}）")

    conn.commit()

    # 5. 验证结果
    print("\n--- 修改后待办任务 ---")
    cur.execute("""
        SELECT id, title, priority, status, due_date
        FROM tasks
        WHERE status IN ('todo', 'in_progress') AND is_deleted = 0
        ORDER BY due_date
    """)
    for t in cur.fetchall():
        is_overdue = "⚠️ 已逾期" if t[4] and t[4] < date.today().isoformat() else ""
        print(f"  {t[1]} | {t[2]} | 截止={t[4]} {is_overdue}")

    # 统计
    cur.execute("SELECT priority, COUNT(*) FROM tasks WHERE status IN ('todo', 'in_progress') AND is_deleted = 0 GROUP BY priority")
    print(f"\n优先级分布: {dict(cur.fetchall())}")
    cur.execute("SELECT COUNT(*) FROM tasks WHERE status IN ('todo', 'in_progress') AND is_deleted = 0 AND due_date < ?", (date.today().isoformat(),))
    print(f"已逾期任务数: {cur.fetchone()[0]}")

    conn.close()

if __name__ == "__main__":
    from datetime import datetime
    main()
