"""v1.7 里程碑收款绑定工具模块。

提供里程碑收款状态流转校验、收款汇总计算、逾期检测等核心功能。
"""
import sqlite3
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Any, Optional


# 收款状态白名单
PAYMENT_STATUS_WHITELIST = ["unpaid", "invoiced", "received"]

# 收款状态流转规则
PAYMENT_VALID_TRANSITIONS = {
    "unpaid": ["invoiced", "received"],  # unpaid 可以直接跳到 received（零金额里程碑）
    "invoiced": ["received"],  # invoiced 后只能到 received
    "received": [],  # 终态
}


def validate_payment_transition_sync(
    db: sqlite3.Connection,
    milestone_id: int,
    target_status: str,
) -> Dict[str, Any]:
    """校验里程碑是否满足收款状态流转条件。

    Args:
        db: 同步数据库连接
        milestone_id: 里程碑ID
        target_status: 目标状态（invoiced 或 received）

    Returns:
        {"allowed": bool, "reason": str}
    """
    # 校验目标状态是否在白名单中
    if target_status not in PAYMENT_STATUS_WHITELIST:
        return {"allowed": False, "reason": f"无效的收款状态: {target_status}"}

    # 查询里程碑当前状态
    cur = db.cursor()
    cur.execute("""
        SELECT payment_status, is_completed
        FROM milestones
        WHERE id = ?
    """, (milestone_id,))
    row = cur.fetchone()

    if not row:
        return {"allowed": False, "reason": "里程碑不存在"}

    current_payment_status, is_completed = row

    # 校验状态流转是否合法
    allowed_transitions = PAYMENT_VALID_TRANSITIONS.get(current_payment_status, [])
    if target_status not in allowed_transitions:
        return {
            "allowed": False,
            "reason": f"收款状态不能从 '{current_payment_status}' 变更为 '{target_status}'"
        }

    # invoiced 状态要求里程碑已完成
    if target_status == "invoiced":
        # is_completed 为 True 表示已完成
        if not is_completed:
            return {
                "allowed": False,
                "reason": "仅已完成的里程碑可以标记为已开票"
            }

    return {"allowed": True, "reason": ""}


def get_project_payment_summary(
    db: sqlite3.Connection,
    project_id: int,
) -> Dict[str, Any]:
    """计算项目收款汇总。

    Args:
        db: 同步数据库连接
        project_id: 项目ID

    Returns:
        {
            "total_contract_amount": Decimal,
            "total_milestone_amount": Decimal,
            "received_amount": Decimal,
            "invoiced_amount": Decimal,
            "unpaid_amount": Decimal,
        }
    """
    cur = db.cursor()

    # 获取合同总额
    cur.execute("""
        SELECT COALESCE(SUM(c.amount), 0)
        FROM contracts c
        WHERE c.project_id = ? AND c.is_deleted = 0
    """, (project_id,))
    total_contract_amount = Decimal(str(cur.fetchone()[0] or 0))

    # 获取里程碑收款汇总
    cur.execute("""
        SELECT
            COALESCE(SUM(payment_amount), 0) as total_amount,
            COALESCE(SUM(CASE WHEN payment_status = 'received' THEN payment_amount ELSE 0 END), 0) as received,
            COALESCE(SUM(CASE WHEN payment_status = 'invoiced' THEN payment_amount ELSE 0 END), 0) as invoiced,
            COALESCE(SUM(CASE WHEN payment_status = 'unpaid' THEN payment_amount ELSE 0 END), 0) as unpaid
        FROM milestones
        WHERE project_id = ? AND is_deleted = 0
    """, (project_id,))
    row = cur.fetchone()

    total_milestone_amount = Decimal(str(row[0] or 0))
    received_amount = Decimal(str(row[1] or 0))
    invoiced_amount = Decimal(str(row[2] or 0))
    unpaid_amount = Decimal(str(row[3] or 0))

    return {
        "total_contract_amount": round(total_contract_amount, 2),
        "total_milestone_amount": round(total_milestone_amount, 2),
        "received_amount": round(received_amount, 2),
        "invoiced_amount": round(invoiced_amount, 2),
        "unpaid_amount": round(unpaid_amount, 2),
    }


def get_overdue_payment_milestones(
    db: sqlite3.Connection,
    project_id: int,
) -> List[Dict[str, Any]]:
    """返回逾期未收款里程碑列表。

    逾期条件：
    1. payment_due_date < 今日
    2. payment_status != 'received'

    Args:
        db: 同步数据库连接
        project_id: 项目ID

    Returns:
        [
            {
                "id": int,
                "title": str,
                "payment_amount": Decimal,
                "payment_due_date": date,
                "payment_status": str,
                "days_overdue": int,
            }
        ]
    """
    cur = db.cursor()
    today = date.today()

    cur.execute("""
        SELECT
            id, title, payment_amount, payment_due_date, payment_status
        FROM milestones
        WHERE project_id = ?
          AND is_deleted = 0
          AND payment_due_date IS NOT NULL
          AND payment_due_date < ?
          AND payment_status != 'received'
        ORDER BY payment_due_date ASC
    """, (project_id, today.isoformat()))

    rows = cur.fetchall()
    result = []

    for row in rows:
        milestone_id, title, payment_amount, payment_due_date, payment_status = row
        due_date = datetime.fromisoformat(payment_due_date).date() if isinstance(payment_due_date, str) else payment_due_date
        days_overdue = (today - due_date).days

        result.append({
            "id": milestone_id,
            "title": title,
            "payment_amount": float(Decimal(str(payment_amount))) if payment_amount else 0.0,
            "payment_due_date": payment_due_date,
            "payment_status": payment_status,
            "days_overdue": days_overdue,
        })

    return result
