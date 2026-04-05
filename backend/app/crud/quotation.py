from datetime import date
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud.base import CRUDBase
from app.models.quotation import Quotation
from app.schemas.quotation import QuotationCreate, QuotationUpdate


class CRUDQuotation(CRUDBase[Quotation, QuotationCreate, QuotationUpdate]):
    async def generate_quotation_number(self, db: AsyncSession) -> str:
        today = date.today()
        prefix = f"BJ-{today.strftime('%Y%m%d')}"
        result = await db.execute(
            select(Quotation.quotation_number)
            .where(Quotation.quotation_number.like(f"{prefix}%"))
            .order_by(Quotation.quotation_number.desc())
        )
        existing = result.scalars().first()
        if existing:
            seq = int(existing.split("-")[-1]) + 1
        else:
            seq = 1
        return f"{prefix}-{seq:03d}"


quotation = CRUDQuotation(Quotation)
