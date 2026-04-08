from datetime import date
from typing import Any, Dict, List, Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud.base import CRUDBase
from app.models.quotation import Quotation
from app.schemas.quotation import QuotationCreate, QuotationUpdate


class CRUDQuotation(CRUDBase[Quotation, QuotationCreate, QuotationUpdate]):
    async def generate_quote_no(self, db: AsyncSession) -> str:
        """生成报价单编号：BJ-YYYYMMDD-序号。"""
        today = date.today()
        prefix = f"BJ-{today.strftime('%Y%m%d')}"
        result = await db.execute(
            select(Quotation.quote_no)
            .where(Quotation.quote_no.like(f"{prefix}%"))
            .order_by(Quotation.quote_no.desc())
        )
        existing = result.scalars().first()
        if existing:
            seq = int(existing.split("-")[-1]) + 1
        else:
            seq = 1
        return f"{prefix}-{seq:03d}"

    async def list(
        self, db: AsyncSession, skip: int = 0, limit: int = 20,
        filters: Optional[Dict[str, Any]] = None, search: Optional[str] = None,
    ) -> tuple[List[Quotation], int]:
        query = select(Quotation).where(Quotation.is_deleted == False)
        count_query = select(func.count()).select_from(Quotation).where(Quotation.is_deleted == False)

        if filters:
            for key, value in filters.items():
                if value is not None:
                    query = query.where(getattr(Quotation, key) == value)
                    count_query = count_query.where(getattr(Quotation, key) == value)

        if search:
            pattern = f"%{search}%"
            query = query.where(Quotation.title.ilike(pattern))
            count_query = count_query.where(Quotation.title.ilike(pattern))

        count_result = await db.execute(count_query)
        total = count_result.scalar()

        query = query.offset(skip).limit(limit).order_by(Quotation.created_at.desc())
        result = await db.execute(query)
        items = result.scalars().all()
        return list(items), total


quotation = CRUDQuotation(Quotation)
