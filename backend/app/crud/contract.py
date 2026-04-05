from datetime import date
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud.base import CRUDBase
from app.models.contract import Contract
from app.schemas.contract import ContractCreate, ContractUpdate


class CRUDContract(CRUDBase[Contract, ContractCreate, ContractUpdate]):
    async def generate_contract_no(self, db: AsyncSession) -> str:
        today = date.today()
        prefix = f"HT-{today.strftime('%Y%m%d')}"
        result = await db.execute(
            select(Contract.contract_no)
            .where(Contract.contract_no.like(f"{prefix}%"))
            .order_by(Contract.contract_no.desc())
        )
        existing = result.scalars().first()
        if existing:
            seq = int(existing.split("-")[-1]) + 1
        else:
            seq = 1
        return f"{prefix}-{seq:03d}"

    async def sync_amount_to_project(self, db: AsyncSession, contract: Contract) -> None:
        if contract.project_id:
            from app.models.project import Project

            result = await db.execute(select(Project).where(Project.id == contract.project_id))
            proj = result.scalar_one_or_none()
            if proj:
                proj.budget = contract.amount
                db.add(proj)
                await db.commit()


contract = CRUDContract(Contract)
