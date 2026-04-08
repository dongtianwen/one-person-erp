"""v1.7 项目关闭强制条件工具模块。

提供项目关闭条件校验、关闭操作等核心功能。
"""
import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Any


# 项目关闭条件白名单
PROJECT_CLOSE_CHECKLIST = {
    "all_milestones_completed": "所有里程碑 is_completed = 1",
    "final_acceptance_passed": "acceptances 表中该项目最新的验收记录 result=passed",
    "payment_cleared": "所有里程碑 payment_status=received 或 payment_amount=0",
    "deliverables_archived": "至少存在一条 deliverable 记录",
}


def check_project_close_conditions(
    db: sqlite3.Connection,
    project_id: int,
) -> Dict[str, Any]:
    """检查项目是否满足关闭条件。

    Args:
        db: 同步数据库连接
        project_id: 项目ID

    Returns:
        {
            "all_milestones_completed": bool,
            "final_acceptance_passed": bool,
            "payment_cleared": bool,
            "deliverables_archived": bool,
            "can_close": bool,
            "blocking_items": ["..."]
        }
    """
    cur = db.cursor()
    blocking_items = []

    # 1. 检查所有里程碑是否已完成
    cur.execute("""
        SELECT COUNT(*) FROM milestones
        WHERE project_id = ? AND is_deleted = 0 AND is_completed = 0
    """, (project_id,))
    incomplete_milestones = cur.fetchone()[0]
    all_milestones_completed = incomplete_milestones == 0
    if not all_milestones_completed:
        blocking_items.append(f"有 {incomplete_milestones} 个里程碑未完成")

    # 2. 检查最终验收是否通过（严格按零章 0.2 判定）
    # 注意：acceptances 表使用 result 字段存储验收结果（不是 status）
    # 使用最新的验收记录（按 created_at DESC）作为最终验收
    cur.execute("""
        SELECT result FROM acceptances
        WHERE project_id = ?
        ORDER BY created_at DESC
        LIMIT 1
    """, (project_id,))
    row = cur.fetchone()
    final_acceptance_passed = row is not None and row[0] == "passed"
    if not final_acceptance_passed:
        if row is None:
            blocking_items.append("未进行最终验收")
        else:
            blocking_items.append(f"最终验收状态为 {row[0]}，未通过")

    # 3. 检查收款是否已结清
    cur.execute("""
        SELECT COUNT(*) FROM milestones
        WHERE project_id = ? AND is_deleted = 0
          AND payment_status != 'received'
          AND (payment_amount IS NOT NULL AND payment_amount > 0)
    """, (project_id,))
    unpaid_milestones = cur.fetchone()[0]
    payment_cleared = unpaid_milestones == 0
    if not payment_cleared:
        blocking_items.append(f"有 {unpaid_milestones} 个里程碑收款未到账")

    # 4. 检查交付物是否已归档
    cur.execute("""
        SELECT COUNT(*) FROM deliverables
        WHERE project_id = ? AND is_deleted = 0
    """, (project_id,))
    deliverable_count = cur.fetchone()[0]
    deliverables_archived = deliverable_count > 0
    if not deliverables_archived:
        blocking_items.append("未上传任何交付物")

    can_close = all([
        all_milestones_completed,
        final_acceptance_passed,
        payment_cleared,
        deliverables_archived,
    ])

    return {
        "all_milestones_completed": all_milestones_completed,
        "final_acceptance_passed": final_acceptance_passed,
        "payment_cleared": payment_cleared,
        "deliverables_archived": deliverables_archived,
        "can_close": can_close,
        "blocking_items": blocking_items,
    }


def close_project_sync(
    db: sqlite3.Connection,
    project_id: int,
) -> Dict[str, Any]:
    """关闭项目（原子事务）。

    流程：
    1. 校验关闭条件
    2. 检查项目是否已关闭
    3. 更新状态为 completed
    4. 写入 closed_at 和 close_checklist 快照

    Args:
        db: 同步数据库连接
        project_id: 项目ID

    Returns:
        {"success": bool, "message": str, "project": dict}
    """
    cur = db.cursor()

    # 1. 检查项目是否存在
    cur.execute("SELECT id, status FROM projects WHERE id = ?", (project_id,))
    project = cur.fetchone()
    if not project:
        return {"success": False, "message": "项目不存在"}

    project_id_from_db, current_status = project

    # 2. 检查是否已关闭
    if current_status == "completed":
        return {"success": False, "message": "项目已关闭，无法重复关闭"}

    # 3. 校验关闭条件
    conditions = check_project_close_conditions(db, project_id)
    if not conditions["can_close"]:
        return {
            "success": False,
            "message": "项目不满足关闭条件",
            "blocking_items": conditions["blocking_items"],
        }

    # 4. 执行关闭（原子事务）
    try:
        closed_at = datetime.utcnow().isoformat()
        checklist_snapshot = json.dumps({
            "all_milestones_completed": conditions["all_milestones_completed"],
            "final_acceptance_passed": conditions["final_acceptance_passed"],
            "payment_cleared": conditions["payment_cleared"],
            "deliverables_archived": conditions["deliverables_archived"],
        }, ensure_ascii=False)

        cur.execute("""
            UPDATE projects
            SET status = 'completed',
                closed_at = ?,
                close_checklist = ?
            WHERE id = ?
        """, (closed_at, checklist_snapshot, project_id))

        db.commit()

        # 获取更新后的项目信息
        cur.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        updated_project = cur.fetchone()

        return {
            "success": True,
            "message": "项目已关闭",
            "project_id": project_id,
            "closed_at": closed_at,
        }

    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "message": f"关闭项目失败: {str(e)}",
        }
