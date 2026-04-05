from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud.base import CRUDBase
from app.models.customer_asset import CustomerAsset
from app.schemas.customer_asset import CustomerAssetCreate, CustomerAssetUpdate


class CRUDCustomerAsset(CRUDBase[CustomerAsset, CustomerAssetCreate, CustomerAssetUpdate]):
    async def list_by_customer(
        self, db: AsyncSession, customer_id: int
    ) -> list[CustomerAsset]:
        result = await db.execute(
            select(CustomerAsset)
            .where(CustomerAsset.customer_id == customer_id, CustomerAsset.is_deleted == False)
            .order_by(CustomerAsset.expiry_date.asc().nulls_last())
        )
        return list(result.scalars().all())


customer_asset = CRUDCustomerAsset(CustomerAsset)
