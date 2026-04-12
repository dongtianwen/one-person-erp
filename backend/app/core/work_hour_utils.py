"""v1.7 工时偏差记录工具模块。

提供工时偏差计算、汇总统计等核心功能。
"""
import sqlite3
from decimal import Decimal
from typing import Dict, List, Any, Optional
from datetime import date


# 工时偏差阈值（后端唯一判断来源）
WORK_HOUR_DEVIATION_THRESHOLD = 0.20  # 20%


def calculate_deviation(
    estimated_hours: Optional[int],
    actual_hours: float,
) -> Dict[str, Any]:
    """计算工时偏差。

    Args:
        estimated_hours: 预计工时（小时），可能为 None
        actual_hours: 实际工时（小时）

    Returns:
        {
            "deviation_rate": float | None,  # 偏差率，无预计工时时为 None
            "deviation_exceeds_threshold": bool,  # 是否超过阈值
        }
    """
    if estimated_hours is None or estimated_hours <= 0:
        return {
            "deviation_rate": None,
            "deviation_exceeds_threshold": False,
        }

    deviation_rate = (actual_hours - estimated_hours) / estimated_hours
    exceeds_threshold = abs(deviation_rate) > WORK_HOUR_DEVIATION_THRESHOLD

    return {
        "deviation_rate": round(deviation_rate, 4),
        "deviation_exceeds_threshold": exceeds_threshold,
    }


def check_deviation_exceeds_threshold(
    estimated_hours: Optional[int],
    actual_hours: float,
) -> bool:
    """检查工时偏差是否超过阈值。

    Args:
        estimated_hours: 预计工时（小时），可能为 None
        actual_hours: 实际工时（小时）

    Returns:
        bool: 是否超过阈值
    """
    result = calculate_deviation(estimated_hours, actual_hours)
    return result["deviation_exceeds_threshold"]


def get_work_hour_summary(
    db: sqlite3.Connection,
    project_id: int,
) -> Dict[str, Any]:
    """获取项目工时汇总。

    Args:
        db: 同步数据库连接
        project_id: 项目ID

    Returns:
        {
            "estimated_hours": int | None,
            "actual_hours_total": float,
            "deviation_rate": float | None,
            "deviation_exceeds_threshold": bool,
            "logs": [
                {
                    "id": int,
                    "log_date": str,
                    "hours_spent": float,
                    "task_description": str,
                    "deviation_note": str | None,
                }
            ]
        }
    """
    cur = db.cursor()

    # 获取项目预计工时
    cur.execute("""
        SELECT estimated_hours FROM projects
        WHERE id = ?
    """, (project_id,))
    row = cur.fetchone()
    estimated_hours = row[0] if row else None

    # 获取实际工时总计
    cur.execute("""
        SELECT COALESCE(SUM(hours_spent), 0) FROM work_hour_logs
        WHERE project_id = ?
    """, (project_id,))
    actual_hours_total = float(cur.fetchone()[0])

    # 计算偏差
    deviation_info = calculate_deviation(estimated_hours, actual_hours_total)

    # 获取工时记录列表（按日期倒序）
    cur.execute("""
        SELECT id, log_date, hours_spent, task_description, deviation_note, created_at
        FROM work_hour_logs
        WHERE project_id = ?
        ORDER BY log_date DESC, created_at DESC
    """, (project_id,))
    rows = cur.fetchall()

    logs = []
    for row in rows:
        logs.append({
            "id": row[0],
            "log_date": row[1],
            "hours_spent": float(row[2]),
            "task_description": row[3],
            "deviation_note": row[4],
            "created_at": row[5],
        })

    return {
        "estimated_hours": estimated_hours,
        "actual_hours_total": round(actual_hours_total, 2),
        "deviation_rate": deviation_info["deviation_rate"],
        "deviation_exceeds_threshold": deviation_info["deviation_exceeds_threshold"],
        "logs": logs,
    }


def validate_work_hour_log(
    hours_spent: float,
    deviation_exceeds_threshold: bool,
    deviation_note: Optional[str],
) -> Dict[str, Any]:
    """校验工时记录。

    Args:
        hours_spent: 工时数
        deviation_exceeds_threshold: 是否超过阈值
        deviation_note: 偏差备注

    Returns:
        {"allowed": bool, "reason": str}
    """
    # 校验工时范围
    if hours_spent <= 0:
        return {"allowed": False, "reason": "工时必须大于 0"}

    if hours_spent > 24:
        return {"allowed": False, "reason": "工时不得超过 24 小时"}

    # 超过阈值时必须有偏差备注
    if deviation_exceeds_threshold and not deviation_note:
        return {"allowed": False, "reason": "偏差超过阈值，必须填写偏差备注"}

    return {"allowed": True, "reason": ""}
