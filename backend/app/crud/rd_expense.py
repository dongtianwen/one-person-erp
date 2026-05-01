import logging
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date

from app.models.rd_expense import RdExpense
from app.schemas.rd_expense import RdExpenseCreate, RdExpenseUpdate
from app.core.constants import DECIMAL_PLACES, RD_NO_PREFIX, RD_VALID_TRANSITIONS

logger = logging.getLogger(__name__)


class CRUDRdExpense:

    async def get(self, db: AsyncSession, record_id: int) -> RdExpense | None:
        result = await db.execute(
            select(RdExpense).where(RdExpense.id == record_id, RdExpense.is_deleted == False)
        )
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        project_id: int | None = None,
        rd_category: str | None = None,
        status: str | None = None,
        year: int | None = None,
        quarter: int | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[RdExpense], int]:
        conditions = [RdExpense.is_deleted == False]
        if project_id is not None:
            conditions.append(RdExpense.project_id == project_id)
        if rd_category is not None:
            conditions.append(RdExpense.rd_category == rd_category)
        if status is not None:
            conditions.append(RdExpense.status == status)

        if year is not None:
            period_prefix = f"{year}"
            if quarter is not None:
                start_month = (quarter - 1) * 3 + 1
                periods = [f"{year}-{m:02d}" for m in range(start_month, start_month + 3)]
                conditions.append(RdExpense.accounting_period.in_(periods))
            else:
                conditions.append(RdExpense.accounting_period.like(f"{period_prefix}%"))

        where_clause = and_(*conditions)

        count_query = select(func.count(RdExpense.id)).where(where_clause)
        total = (await db.execute(count_query)).scalar() or 0

        query = (
            select(RdExpense)
            .options(selectinload(RdExpense.project), selectinload(RdExpense.contract))
            .where(where_clause)
            .order_by(RdExpense.expense_date.desc(), RdExpense.created_at.desc())
            .offset(skip).limit(limit)
        )
        result = await db.execute(query)
        items = list(result.scalars().all())
        return items, total

    async def create(self, db: AsyncSession, obj_in: RdExpenseCreate, rd_no: str) -> RdExpense:
        from datetime import datetime
        accounting_period = obj_in.expense_date.strftime("%Y-%m")

        db_obj = RdExpense(
            rd_no=rd_no,
            rd_category=obj_in.rd_category,
            rd_sub_category=obj_in.rd_sub_category,
            amount=round(obj_in.amount, DECIMAL_PLACES),
            tax_amount=round(obj_in.tax_amount or 0, DECIMAL_PLACES),
            total_amount=round(
                (obj_in.amount or 0) + (obj_in.tax_amount or 0), DECIMAL_PLACES
            ),
            expense_date=obj_in.expense_date,
            accounting_period=accounting_period,
            project_id=obj_in.project_id,
            finance_record_id=obj_in.finance_record_id,
            contract_id=obj_in.contract_id,
            description=obj_in.description or "",
            vendor_name=obj_in.vendor_name,
            invoice_no=obj_in.invoice_no,
            has_invoice=obj_in.has_invoice,
            invoice_type=obj_in.invoice_type,
            status="draft",
            notes=obj_in.notes,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(self, db: AsyncSession, db_obj: RdExpense, obj_in: RdExpenseUpdate) -> RdExpense:
        update_data = obj_in.model_dump(exclude_unset=True)

        if "expense_date" in update_data or "amount" in update_data or "tax_amount" in update_data:
            new_date = update_data.get("expense_date", db_obj.expense_date)
            new_amount = update_data.get("amount", db_obj.amount)
            new_tax = update_data.get("tax_amount", db_obj.tax_amount)
            update_data["accounting_period"] = new_date.strftime("%Y-%m") if new_date else db_obj.accounting_period
            update_data["total_amount"] = round((new_amount or 0) + (new_tax or 0), DECIMAL_PLACES)
            if "amount" in update_data:
                update_data["amount"] = round(update_data["amount"], DECIMAL_PLACES)
            if "tax_amount" in update_data:
                update_data["tax_amount"] = round(update_data["tax_amount"], DECIMAL_PLACES)

        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def delete(self, db: AsyncSession, record_id: int) -> bool:
        db_obj = await self.get(db, record_id)
        if db_obj is None:
            return False
        if db_obj.status != "draft":
            return False
        db_obj.is_deleted = True
        await db.commit()
        return True

    async def update_status(self, db: AsyncSession, db_obj: RdExpense, new_status: str) -> RdExpense:
        current = db_obj.status
        valid_next = RD_VALID_TRANSITIONS.get(current, [])
        if new_status not in valid_next:
            raise ValueError(f"Invalid status transition: {current} -> {new_status}")
        db_obj.status = new_status
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def get_summary(
        self,
        db: AsyncSession,
        *,
        year: int | None = None,
        quarter: int | None = None,
        accounting_period: str | None = None,
        project_id: int | None = None,
    ) -> dict:
        conditions = [RdExpense.is_deleted == False]

        if accounting_period:
            conditions.append(RdExpense.accounting_period == accounting_period)
        elif year:
            period_prefix = f"{year}"
            if quarter:
                start_month = (quarter - 1) * 3 + 1
                periods = [f"{year}-{m:02d}" for m in range(start_month, start_month + 3)]
                conditions.append(RdExpense.accounting_period.in_(periods))
            else:
                conditions.append(RdExpense.accounting_period.like(f"{period_prefix}%"))

        if project_id:
            conditions.append(RdExpense.project_id == project_id)

        where_clause = and_(*conditions)

        from app.core.constants import RD_CATEGORY_LABELS

        result = await db.execute(
            select(
                RdExpense.rd_category,
                func.sum(RdExpense.amount).label("total_amount"),
                func.sum(RdExpense.tax_amount).label("total_tax"),
                func.sum(RdExpense.total_amount).label("total_grand"),
                func.count(RdExpense.id).label("count"),
            )
            .where(where_clause)
            .group_by(RdExpense.rd_category)
        )

        categories = []
        grand_amount = 0
        grand_tax = 0
        grand_total = 0

        for row in result.all():
            cat_key = row[0]
            cat_label = RD_CATEGORY_LABELS.get(cat_key, cat_key)
            amt = float(row[1] or 0)
            tax = float(row[2] or 0)
            total = float(row[3] or 0)
            cnt = int(row[4] or 0)
            categories.append({
                "category": cat_key,
                "category_label": cat_label,
                "amount": round(amt, DECIMAL_PLACES),
                "tax_amount": round(tax, DECIMAL_PLACES),
                "total_amount": round(total, DECIMAL_PLACES),
                "count": cnt,
            })
            grand_amount += amt
            grand_tax += tax
            grand_total += total

        period_str = accounting_period or (f"{year}Q{quarter}" if quarter else str(year))
        return {
            "period": period_str,
            "total_amount": round(grand_amount, DECIMAL_PLACES),
            "total_tax_amount": round(grand_tax, DECIMAL_PLACES),
            "total_grand": round(grand_total, DECIMAL_PLACES),
            "categories": categories,
        }

    async def generate_rd_no(self, db: AsyncSession) -> str:
        today = date.today()
        prefix = f"{RD_NO_PREFIX}-{today.strftime('%Y%m%d')}"
        result = await db.execute(
            select(func.max(RdExpense.rd_no))
            .where(RdExpense.rd_no.like(f"{prefix}%"))
        )
        max_no = result.scalar() or f"{prefix}-000"
        last_seq = int(max_no.split("-")[-1])
        next_seq = last_seq + 1
        return f"{prefix}-{next_seq:03d}"


rd_expense = CRUDRdExpense()
