from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud.base import CRUDBase
from app.models.customer import Customer
from app.schemas.customer import CustomerCreate, CustomerUpdate


class CRUDCustomer(CRUDBase[Customer, CustomerCreate, CustomerUpdate]):
    async def get_by_company_and_contact(self, db: AsyncSession, company: str, contact_person: str) -> Customer | None:
        result = await db.execute(
            select(Customer).where(
                Customer.company == company, Customer.contact_person == contact_person, Customer.is_deleted == False
            )
        )
        return result.scalar_one_or_none()

    async def get_stats_by_status(self, db: AsyncSession) -> dict:
        from sqlalchemy import func

        result = await db.execute(
            select(Customer.status, func.count(Customer.id))
            .where(Customer.is_deleted == False)
            .group_by(Customer.status)
        )
        return {row[0]: row[1] for row in result.all()}

    async def get_stats_by_source(self, db: AsyncSession) -> dict:
        from sqlalchemy import func

        result = await db.execute(
            select(Customer.source, func.count(Customer.id))
            .where(Customer.is_deleted == False)
            .group_by(Customer.source)
        )
        return {row[0]: row[1] for row in result.all()}

    async def has_associations(self, db: AsyncSession, customer_id: int) -> bool:
        from app.models.project import Project
        from app.models.contract import Contract

        proj_result = await db.execute(
            select(Project.id).where(Project.customer_id == customer_id, Project.is_deleted == False).limit(1)
        )
        if proj_result.first():
            return True
        contract_result = await db.execute(
            select(Contract.id).where(Contract.customer_id == customer_id, Contract.is_deleted == False).limit(1)
        )
        return contract_result.first() is not None


customer = CRUDCustomer(Customer)
