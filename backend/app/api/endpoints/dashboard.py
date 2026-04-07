import os
import shutil
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.customer import Customer
from app.models.project import Project, Task
from app.models.contract import Contract
from app.models.finance import FinanceRecord
from app.crud import finance as finance_crud
from app.config import settings

router = APIRouter()


@router.get("")
async def get_dashboard(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Trigger point B: Throttled overdue check on dashboard request
    try:
        from app.services.overdue_check import run_dashboard_check
        await run_dashboard_check(db)
    except Exception:
        pass  # Non-blocking: dashboard should still load

    now = datetime.utcnow()
    year, month = now.year, now.month

    try:
        monthly_summary = await finance_crud.finance_record.get_monthly_summary(db, year, month)
    except Exception:
        monthly_summary = {"income": 0, "expense": 0, "profit": 0}

    try:
        active_result = await db.execute(
            select(func.count(Project.id)).where(
                Project.status.notin_(["delivery", "paused"]), Project.is_deleted == False
            )
        )
        active_projects = active_result.scalar() or 0
    except Exception:
        active_projects = 0

    try:
        total_result = await db.execute(select(func.count(Customer.id)).where(Customer.is_deleted == False))
        total_customers = total_result.scalar() or 0

        deal_result = await db.execute(
            select(func.count(Customer.id)).where(Customer.status == "deal", Customer.is_deleted == False)
        )
        deal_customers = deal_result.scalar() or 0

        conversion_rate = (deal_customers / total_customers * 100) if total_customers > 0 else 0
    except Exception:
        conversion_rate = 0

    try:
        accounts_receivable = await finance_crud.finance_record.get_accounts_receivable(db)
    except Exception:
        accounts_receivable = 0

    # Quotation conversion rate
    quotation_conversion_rate = 0.0
    try:
        from app.models.quotation import Quotation
        total_q = await db.execute(
            select(func.count(Quotation.id)).where(
                Quotation.status != "draft",
                Quotation.is_deleted == False,
            )
        )
        accepted_q = await db.execute(
            select(func.count(Quotation.id)).where(
                Quotation.status == "accepted",
                Quotation.is_deleted == False,
            )
        )
        total_q_count = total_q.scalar() or 0
        accepted_q_count = accepted_q.scalar() or 0
        if total_q_count > 0:
            quotation_conversion_rate = round(accepted_q_count / total_q_count * 100, 2)
    except Exception:
        pass

    # v1.5: Active maintenance count
    active_maintenance_count = 0
    try:
        from app.models.maintenance import MaintenancePeriod
        m_result = await db.execute(
            select(func.count(MaintenancePeriod.id)).where(
                MaintenancePeriod.status == "active",
            )
        )
        active_maintenance_count = m_result.scalar() or 0
    except Exception:
        pass

    return {
        "monthly_income": monthly_summary["income"],
        "monthly_expense": monthly_summary["expense"],
        "monthly_profit": monthly_summary["profit"],
        "active_projects": active_projects,
        "customer_conversion_rate": round(conversion_rate, 2),
        "accounts_receivable": accounts_receivable,
        "quotation_conversion_rate": quotation_conversion_rate,
        "active_maintenance_count": active_maintenance_count,
    }


@router.get("/unsettled-warning")
async def get_unsettled_warning(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        data = await finance_crud.finance_record.get_unsettled_summary(db)
        return data
    except Exception:
        return {"count": 0, "total_amount": 0}


@router.get("/revenue-trend")
async def get_revenue_trend(
    months: int = Query(12, ge=1, le=24),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        trend = []
        now = datetime.utcnow()
        for i in range(months - 1, -1, -1):
            target_month = now.month - i
            target_year = now.year
            while target_month <= 0:
                target_month += 12
                target_year -= 1
            summary = await finance_crud.finance_record.get_monthly_summary(db, target_year, target_month)
            trend.append(
                {
                    "month": f"{target_year}-{target_month:02d}",
                    "income": summary["income"],
                    "expense": summary["expense"],
                }
            )
        return trend
    except Exception:
        return []


@router.get("/customer-funnel")
async def get_customer_funnel(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        result = await db.execute(
            select(Customer.status, func.count(Customer.id))
            .where(Customer.is_deleted == False)
            .group_by(Customer.status)
        )
        stats = {row[0]: row[1] for row in result.all()}
        return {
            "potential": stats.get("potential", 0),
            "follow_up": stats.get("follow_up", 0),
            "deal": stats.get("deal", 0),
            "lost": stats.get("lost", 0),
        }
    except Exception:
        return {"potential": 0, "follow_up": 0, "deal": 0, "lost": 0}


@router.get("/project-status")
async def get_project_status_distribution(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    try:
        result = await db.execute(
            select(Project.status, func.count(Project.id)).where(Project.is_deleted == False).group_by(Project.status)
        )
        return {row[0]: row[1] for row in result.all()}
    except Exception:
        return {}


@router.get("/todos")
async def get_todo_items(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        from sqlalchemy import case
        from datetime import date, timedelta
        from app.models.reminder import Reminder

        priority_order = case(
            (Task.priority == "high", 3),
            (Task.priority == "medium", 2),
            (Task.priority == "low", 1),
            else_=0,
        )
        task_result = await db.execute(
            select(Task)
            .where(Task.status.in_(["todo", "in_progress"]), Task.is_deleted == False)
            .order_by(priority_order.desc(), Task.due_date.asc())
            .limit(10)
        )
        tasks = task_result.scalars().all()

        month_later = date.today() + timedelta(days=30)
        contract_result = await db.execute(
            select(Contract)
            .where(
                Contract.end_date <= month_later,
                Contract.end_date >= date.today(),
                Contract.status.in_(["active", "executing"]),
                Contract.is_deleted == False,
            )
            .limit(5)
        )
        contracts = contract_result.scalars().all()

        # Overdue + upcoming reminders (7-day window)
        reminder_result = await db.execute(
            select(Reminder)
            .where(
                Reminder.status.in_(["pending", "overdue"]),
                Reminder.reminder_date <= month_later,
                Reminder.is_deleted == False,
            )
            .order_by(
                case(
                    (Reminder.status == "overdue", 0),
                    (Reminder.status == "pending", 1),
                    else_=2,
                ),
                Reminder.reminder_date.asc(),
            )
            .limit(10)
        )
        reminders = reminder_result.scalars().all()

        return {
            "tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "project_id": t.project_id,
                    "priority": t.priority,
                    "due_date": str(t.due_date) if t.due_date else None,
                }
                for t in tasks
            ],
            "expiring_contracts": [
                {"id": c.id, "contract_no": c.contract_no, "title": c.title, "end_date": str(c.end_date)}
                for c in contracts
            ],
            "reminders": [
                {
                    "id": r.id,
                    "title": r.title,
                    "reminder_type": r.reminder_type,
                    "reminder_date": str(r.reminder_date),
                    "status": r.status,
                    "is_critical": r.is_critical,
                }
                for r in reminders
            ],
        }
    except Exception:
        return {"tasks": [], "expiring_contracts": [], "reminders": []}


@router.post("/backup")
async def backup_database(
    backup_dir: str = Query("./backups"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db_path = settings.DATABASE_URL.split("///")[-1]
    if not os.path.exists(db_path):
        raise Exception("数据库文件不存在")

    Path(backup_dir).mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, f"shubiao_backup_{timestamp}.db")

    shutil.copy2(db_path, backup_path)

    return {"message": "备份成功", "backup_path": backup_path, "timestamp": timestamp}


@router.get("/backups")
async def list_backups(
    current_user: User = Depends(get_current_user),
):
    """List all backup files with verification status."""
    from app.services.backup import list_backups as get_backups
    return get_backups()


@router.post("/backups/{backup_filename}/verify")
async def verify_backup(
    backup_filename: str,
    current_user: User = Depends(get_current_user),
):
    """Verify a specific backup file's integrity."""
    from app.services.backup import verify_backup as do_verify
    backup_dir = Path("./backups")
    backup_path = str(backup_dir / backup_filename)
    result = do_verify(backup_path)
    return result
