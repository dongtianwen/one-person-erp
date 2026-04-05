from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud.base import CRUDBase
from app.models.finance import FinanceRecord
from app.schemas.finance import FinanceRecordCreate, FinanceRecordUpdate


class CRUDFinanceRecord(CRUDBase[FinanceRecord, FinanceRecordCreate, FinanceRecordUpdate]):
    async def get_monthly_summary(self, db: AsyncSession, year: int, month: int) -> dict:
        from datetime import date

        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month + 1, 1)

        income_result = await db.execute(
            select(func.sum(FinanceRecord.amount)).where(
                FinanceRecord.type == "income",
                FinanceRecord.status.in_(["paid", "confirmed"]),
                FinanceRecord.date >= start_date,
                FinanceRecord.date < end_date,
            )
        )
        income = income_result.scalar() or 0

        expense_result = await db.execute(
            select(func.sum(FinanceRecord.amount)).where(
                FinanceRecord.type == "expense",
                FinanceRecord.status.in_(["paid", "confirmed"]),
                FinanceRecord.date >= start_date,
                FinanceRecord.date < end_date,
            )
        )
        expense = expense_result.scalar() or 0

        return {"income": income, "expense": expense, "profit": income - expense}

    async def get_category_breakdown(self, db: AsyncSession, year: int, month: int) -> dict:
        from datetime import date

        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month + 1, 1)

        result = await db.execute(
            select(FinanceRecord.category, func.sum(FinanceRecord.amount))
            .where(
                FinanceRecord.status.in_(["paid", "confirmed"]),
                FinanceRecord.date >= start_date,
                FinanceRecord.date < end_date,
            )
            .group_by(FinanceRecord.category)
        )
        return {row[0]: row[1] for row in result.all() if row[0]}

    async def get_accounts_receivable(self, db: AsyncSession) -> float:
        from app.models.contract import Contract

        contract_result = await db.execute(
            select(func.sum(Contract.amount)).where(
                Contract.status.in_(["active", "executing"]), Contract.is_deleted == False
            )
        )
        total_contract = contract_result.scalar() or 0

        income_result = await db.execute(
            select(func.sum(FinanceRecord.amount)).where(
                FinanceRecord.type == "income", FinanceRecord.status.in_(["paid", "confirmed"])
            )
        )
        total_income = income_result.scalar() or 0

        return total_contract - total_income

    async def get_funding_source_summary(self, db: AsyncSession, year: int, month: int) -> dict:
        from datetime import date

        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month + 1, 1)

        # Expense by funding source
        result = await db.execute(
            select(FinanceRecord.funding_source, func.sum(FinanceRecord.amount))
            .where(
                FinanceRecord.type == "expense",
                FinanceRecord.status.in_(["paid", "confirmed"]),
                FinanceRecord.date >= start_date,
                FinanceRecord.date < end_date,
            )
            .group_by(FinanceRecord.funding_source)
        )
        funding_sources = {row[0] or "unknown": row[1] for row in result.all()}

        # Unclosed advances (personal_advance with no related reimbursement)
        advances_result = await db.execute(
            select(func.count(FinanceRecord.id)).where(
                FinanceRecord.funding_source == "personal_advance",
                FinanceRecord.is_deleted == False,
                ~FinanceRecord.id.in_(
                    select(FinanceRecord.related_record_id).where(
                        FinanceRecord.related_record_id.isnot(None),
                        FinanceRecord.funding_source == "reimbursement",
                        FinanceRecord.is_deleted == False,
                    )
                ),
            )
        )
        unclosed_advances = advances_result.scalar() or 0

        # Unclosed loans (loan with no related loan_repayment)
        loans_result = await db.execute(
            select(func.count(FinanceRecord.id)).where(
                FinanceRecord.funding_source == "loan",
                FinanceRecord.is_deleted == False,
                ~FinanceRecord.id.in_(
                    select(FinanceRecord.related_record_id).where(
                        FinanceRecord.related_record_id.isnot(None),
                        FinanceRecord.funding_source == "loan_repayment",
                        FinanceRecord.is_deleted == False,
                    )
                ),
            )
        )
        unclosed_loans = loans_result.scalar() or 0

        return {
            "funding_sources": funding_sources,
            "unclosed_advances": unclosed_advances,
            "unclosed_loans": unclosed_loans,
        }

    async def get_unsettled_summary(self, db: AsyncSession) -> dict:
        unsettled_sources = ["personal_advance", "loan"]

        count_result = await db.execute(
            select(func.count(FinanceRecord.id)).where(
                FinanceRecord.funding_source.in_(unsettled_sources),
                FinanceRecord.settlement_status.in_(["open", "partial"]),
                FinanceRecord.is_deleted == False,
            )
        )
        total_count = count_result.scalar() or 0

        amount_result = await db.execute(
            select(func.sum(FinanceRecord.amount)).where(
                FinanceRecord.funding_source.in_(unsettled_sources),
                FinanceRecord.settlement_status.in_(["open", "partial"]),
                FinanceRecord.is_deleted == False,
            )
        )
        total_amount = amount_result.scalar() or 0

        return {"count": total_count, "total_amount": total_amount}


finance_record = CRUDFinanceRecord(FinanceRecord)
