"""
演示项目数据插入脚本
- 不清理现有数据，仅追加6个项目
- 状态覆盖：进行中、已完成、延期
- 进度：10%、35%、60%、80%、100%
- 至少2个延期项目（结束时间已过但未完成）
"""

import sqlite3
import os
import sys
from datetime import date, datetime, timedelta

sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = os.path.join(os.path.dirname(__file__), "shubiao.db")


def now_iso():
    return datetime.utcnow().isoformat()


def days_ago(n):
    return (date.today() - timedelta(days=n)).isoformat()


def days_later(n):
    return (date.today() + timedelta(days=n)).isoformat()


def get_customer_id(cur):
    """获取第一个可用客户ID，如果没有则创建一个"""
    cur.execute("SELECT id FROM customers WHERE is_deleted = 0 LIMIT 1")
    row = cur.fetchone()
    if row:
        return row[0]
    # 创建一个演示客户
    now = now_iso()
    cur.execute("""
        INSERT INTO customers (name, contact_person, phone, email, company, source, status, notes,
                               created_at, updated_at, is_deleted)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
    """, ("演示科技有限公司", "王经理", "138-0000-0000", "demo@example.com",
          "演示科技有限公司", "referral", "active", "演示用客户",
          now, now))
    return cur.lastrowid


def main():
    if not os.path.exists(DB_PATH):
        print(f"数据库文件不存在: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = OFF")
    cur = conn.cursor()
    now = now_iso()

    customer_id = get_customer_id(cur)
    print(f"使用客户ID: {customer_id}")

    # 6个演示项目
    projects = [
        {
            "name": "政务数据标注平台",
            "description": "政务领域多轮对话数据标注平台，支持文本分类、实体抽取、意图识别等标注任务",
            "status": "requirements",
            "budget": 150000.0,
            "start_date": days_ago(15),
            "end_date": days_later(75),
            "progress": 10,
            "estimated_hours": 240,
            "actual_hours": 24,
        },
        {
            "name": "Llama3-8B政务问答模型精调",
            "description": "基于5000条政务问答数据对Llama3-8B进行LoRA精调，目标准确率≥95%",
            "status": "development",
            "budget": 280000.0,
            "start_date": days_ago(60),
            "end_date": days_later(30),
            "progress": 35,
            "estimated_hours": 480,
            "actual_hours": 168,
        },
        {
            "name": "智能客服对话引擎",
            "description": "多轮对话管理系统，支持上下文记忆、意图切换、知识库检索",
            "status": "development",
            "budget": 200000.0,
            "start_date": days_ago(45),
            "end_date": days_later(45),
            "progress": 60,
            "estimated_hours": 360,
            "actual_hours": 216,
        },
        {
            "name": "政务知识图谱构建",
            "description": "从政务公开文档中抽取实体关系，构建可查询的知识图谱",
            "status": "testing",
            "budget": 320000.0,
            "start_date": days_ago(90),
            "end_date": days_later(15),
            "progress": 80,
            "estimated_hours": 600,
            "actual_hours": 480,
        },
        {
            "name": "数据安全脱敏系统",
            "description": "政务数据敏感信息自动识别与脱敏处理系统，支持身份证号、手机号、地址等字段",
            "status": "completed",
            "budget": 180000.0,
            "start_date": days_ago(120),
            "end_date": days_ago(10),
            "progress": 100,
            "estimated_hours": 300,
            "actual_hours": 315,
        },
        {
            "name": "OCR文档识别模块",
            "description": "政务扫描件OCR识别，支持表格提取、印章检测、手写体识别",
            "status": "development",  # 已延期：结束日期已过但未完成
            "budget": 250000.0,
            "start_date": days_ago(100),
            "end_date": days_ago(5),  # 已过期5天
            "progress": 45,
            "estimated_hours": 400,
            "actual_hours": 180,
        },
        {
            "name": "语音合成播报系统",
            "description": "政务大厅智能语音播报系统，支持多音色、多语种、实时合成",
            "status": "requirements",  # 已延期：结束日期已过但未完成
            "budget": 120000.0,
            "start_date": days_ago(80),
            "end_date": days_ago(20),  # 已过期20天
            "progress": 15,
            "estimated_hours": 200,
            "actual_hours": 30,
        },
    ]

    inserted = 0
    for p in projects:
        # 检查是否已存在同名项目（避免重复插入）
        cur.execute("SELECT id FROM projects WHERE name = ? AND is_deleted = 0", (p["name"],))
        if cur.fetchone():
            print(f"  跳过（已存在）: {p['name']}")
            continue

        cur.execute("""
            INSERT INTO projects (name, customer_id, description, status, budget,
                                 start_date, end_date, progress,
                                 estimated_hours, actual_hours,
                                 created_at, updated_at, is_deleted)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
        """, (p["name"], customer_id, p["description"], p["status"], p["budget"],
              p["start_date"], p["end_date"], p["progress"],
              p["estimated_hours"], p["actual_hours"], now, now))
        project_id = cur.lastrowid
        inserted += 1
        print(f"  插入项目 #{project_id}: {p['name']} ({p['status']}, {p['progress']}%)")

        # 为每个项目插入2-3个任务
        tasks = _generate_tasks(p["name"], p["status"], p["progress"])
        for t in tasks:
            cur.execute("""
                INSERT INTO tasks (project_id, title, description, priority, status, assignee, due_date,
                                 created_at, updated_at, is_deleted)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """, (project_id, t["title"], t["description"], t["priority"], t["status"],
                  t["assignee"], t["due_date"], now, now))

    conn.commit()

    # 验证
    cur.execute("SELECT COUNT(*) FROM projects WHERE is_deleted = 0")
    total_projects = cur.fetchone()[0]
    cur.execute("SELECT status, COUNT(*) FROM projects WHERE is_deleted = 0 GROUP BY status")
    status_dist = dict(cur.fetchall())

    print(f"\n完成！本次插入 {inserted} 个项目")
    print(f"项目总数: {total_projects}")
    print(f"状态分布: {status_dist}")

    conn.close()


def _generate_tasks(project_name, project_status, progress):
    """根据项目状态生成合理的任务列表"""
    now = date.today()
    if project_status == "completed":
        return [
            {"title": "需求分析与方案设计", "description": f"{project_name}需求调研与方案评审", "priority": "high", "status": "completed", "assignee": "张三", "due_date": (now - timedelta(days=90)).isoformat()},
            {"title": "核心功能开发", "description": f"{project_name}核心模块编码实现", "priority": "high", "status": "completed", "assignee": "李四", "due_date": (now - timedelta(days=30)).isoformat()},
            {"title": "系统测试与验收", "description": f"{project_name}功能测试与客户验收", "priority": "medium", "status": "completed", "assignee": "王五", "due_date": (now - timedelta(days=10)).isoformat()},
        ]
    elif project_status == "requirements":
        return [
            {"title": "需求调研", "description": f"{project_name}业务流程梳理", "priority": "high", "status": "in_progress", "assignee": "张三", "due_date": (now + timedelta(days=7)).isoformat()},
            {"title": "技术方案设计", "description": f"{project_name}系统架构设计", "priority": "high", "status": "todo", "assignee": "李四", "due_date": (now + timedelta(days=14)).isoformat()},
        ]
    elif project_status == "development":
        return [
            {"title": "数据预处理", "description": f"{project_name}数据清洗与格式化", "priority": "high", "status": "completed", "assignee": "张三", "due_date": (now - timedelta(days=30)).isoformat()},
            {"title": "模型训练与调优", "description": f"{project_name}模型迭代优化", "priority": "high", "status": "in_progress", "assignee": "李四", "due_date": (now + timedelta(days=14)).isoformat()},
            {"title": "API接口开发", "description": f"{project_name}服务端接口实现", "priority": "medium", "status": "in_progress", "assignee": "王五", "due_date": (now + timedelta(days=21)).isoformat()},
        ]
    elif project_status == "testing":
        return [
            {"title": "功能开发", "description": f"{project_name}全部功能模块开发", "priority": "high", "status": "completed", "assignee": "张三", "due_date": (now - timedelta(days=15)).isoformat()},
            {"title": "集成测试", "description": f"{project_name}模块联调与压力测试", "priority": "high", "status": "in_progress", "assignee": "李四", "due_date": (now + timedelta(days=7)).isoformat()},
            {"title": "Bug修复", "description": f"{project_name}测试问题修复", "priority": "medium", "status": "in_progress", "assignee": "王五", "due_date": (now + timedelta(days=10)).isoformat()},
        ]
    return []


if __name__ == "__main__":
    main()
