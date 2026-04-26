"""v2.0 项目复盘自动指标聚合模块。

从项目各关联表中聚合 6 维度指标，生成结构化 JSON 快照，
用于复盘看板的"数据看板区"展示。
"""
import json
from datetime import datetime, date
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import select, func, case, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.profit_utils import calculate_project_profit_v19
from app.core.logging import get_logger

logger = get_logger("retrospective_utils")


async def generate_auto_metrics(
    project_id: int,
    db: AsyncSession,
) -> dict[str, Any]:
    """为指定项目生成 6 维度自动指标。

    Args:
        project_id: 项目 ID
        db: 异步数据库会话

    Returns:
        包含 profit/schedule/milestones/change_orders/acceptance/work_hours
        六个维度的字典，缺失数据时使用合理默认值。
    """
    metrics: dict[str, Any] = {}

    # --- 1. 利润维度 ---
    try:
        report = await calculate_project_profit_v19(db, project_id)
        if "error" not in report:
            rev = report.get("revenue", {})
            cost = report.get("cost", {})
            prof = report.get("profit", {})
            metrics["profit"] = {
                "contract_amount": round(rev.get("contract_amount", 0), 2),
                "received_amount": round(rev.get("received_amount", 0), 2),
                "total_cost": round(cost.get("total_cost", 0), 2),
                "gross_profit": round(prof.get("gross_profit", 0), 2),
                "gross_margin": round(prof.get("gross_margin", 0), 4)
                    if prof.get("gross_margin") is not None else None,
            }
        else:
            metrics["profit"] = _empty_profit()
    except Exception as e:
        logger.warning("利润维度聚合失败 | project_id=%s | error=%s", project_id, e)
        metrics["profit"] = _empty_profit()

    # --- 2. 工期维度 ---
    try:
        from app.models.project import Project
        stmt = select(
            Project.start_date,
            Project.end_date,
            Project.closed_at,
        ).where(Project.id == project_id)
        row = (await db.execute(stmt)).one_or_none()
        if row and row[0]:
            start = row[0] if isinstance(row[0], date) else None
            planned_end = row[1] if isinstance(row[1], date) else None
            closed_at = row[2] if isinstance(row[2], (datetime, date)) else None

            planned_days = (planned_end - start).days if start and planned_end else 0
            actual_days = (closed_at.date() if hasattr(closed_at, 'date') else closed_at - start).days if start and closed_at else 0
            delay_days = max(actual_days - planned_days, 0) if planned_days > 0 else max(0, actual_days - planned_days)

            metrics["schedule"] = {
                "planned_days": planned_days,
                "actual_days": actual_days,
                "delay_days": delay_days,
            }
        else:
            metrics["schedule"] = _empty_schedule()
    except Exception as e:
        logger.warning("工期维度聚合失败 | project_id=%s | error=%s", project_id, e)
        metrics["schedule"] = _empty_schedule()

    # --- 3. 里程碑维度 ---
    try:
        from app.models.project import Milestone
        total_stmt = select(func.count(Milestone.id)).where(
            Milestone.project_id == project_id,
            Milestone.is_deleted == False if hasattr(Milestone, 'is_deleted') else text("1=1"),
        )
        total = (await db.execute(total_stmt)).scalar() or 0

        on_time_stmt = select(func.count(Milestone.id)).where(
            Milestone.project_id == project_id,
            Milestone.is_completed == True,
            Milestone.completed_date <= Milestone.due_date,
        )
        on_time = (await db.execute(on_time_stmt)).scalar() or 0

        delayed_stmt = select(func.count(Milestone.id)).where(
            Milestone.project_id == project_id,
            Milestone.is_completed == True,
            Milestone.completed_date > Milestone.due_date,
        )
        delayed = (await db.execute(delayed_stmt)).scalar() or 0

        metrics["milestones"] = {
            "total": total,
            "on_time": on_time,
            "delayed": delayed,
        }
    except Exception as e:
        logger.warning("里程碑维度聚合失败 | project_id=%s | error=%s", project_id, e)
        metrics["milestones"] = {"total": 0, "on_time": 0, "delayed": 0}

    # --- 4. 变更单维度 ---
    try:
        from app.models.change_order import ChangeOrder
        from app.models.contract import Contract
        co_stmt = select(func.count(ChangeOrder.id)).where(
            ChangeOrder.contract_id.in_(
                select(Contract.id).where(Contract.project_id == project_id)
            ),
            ChangeOrder.status != "draft",
        )
        count = (await db.execute(co_stmt)).scalar() or 0
        impact_desc = f"共{count}次变更"
        if count >= 3:
            impact_desc += f"，增加约{count * 7 // 3}周工作量"
        elif count > 0:
            impact_desc += "，对进度有一定影响"

        metrics["change_orders"] = {
            "count": count,
            "impact_description": impact_desc,
        }
    except Exception as e:
        logger.warning("变更单维度聚合失败 | project_id=%s | error=%s", project_id, e)
        metrics["change_orders"] = {"count": 0, "impact_description": "无变更记录"}

    # --- 5. 验收维度 ---
    try:
        from app.models.acceptance import Acceptance
        total_acc_stmt = select(func.count(Acceptance.id)).where(
            Acceptance.project_id == project_id,
        )
        total_acc = (await db.execute(total_acc_stmt)).scalar() or 0

        passed_stmt = select(func.count(Acceptance.id)).where(
            Acceptance.project_id == project_id,
            Acceptance.result == "passed",
        )
        passed_count = (await db.execute(passed_stmt)).scalar() or 0

        first_pass_rate = round(passed_count / total_acc, 2) if total_acc > 0 else None
        rework_count = max(total_acc - passed_count, 0)

        metrics["acceptance"] = {
            "first_pass_rate": first_pass_rate,
            "rework_count": rework_count,
        }
    except Exception as e:
        logger.warning("验收维度聚合失败 | project_id=%s | error=%s", project_id, e)
        metrics["acceptance"] = {"first_pass_rate": None, "rework_count": 0}

    # --- 6. 工时维度 ---
    try:
        from app.models.project import WorkHourLog
        from app.models.project import Project as ProjModel
        proj_stmt = select(ProjModel.estimated_hours).where(ProjModel.id == project_id)
        estimated = (await db.execute(proj_stmt)).scalar()

        wh_stmt = select(func.sum(WorkHourLog.hours_spent)).where(
            WorkHourLog.project_id == project_id,
        )
        actual_raw = (await db.execute(wh_stmt)).scalar()
        actual = float(actual_raw) if actual_raw else None

        variance = round((actual or 0) - (estimated or 0), 1) if estimated and actual else None

        metrics["work_hours"] = {
            "estimated": estimated,
            "actual": round(actual, 1) if actual else None,
            "variance": variance,
        }
    except Exception as e:
        logger.warning("工时维度聚合失败 | project_id=%s | error=%s", project_id, e)
        metrics["work_hours"] = {"estimated": None, "actual": None, "variance": None}

    return metrics


def _empty_profit() -> dict:
    return {
        "contract_amount": 0,
        "received_amount": 0,
        "total_cost": 0,
        "gross_profit": 0,
        "gross_margin": None,
    }


def _empty_schedule() -> dict:
    return {"planned_days": 0, "actual_days": 0, "delay_days": 0}
