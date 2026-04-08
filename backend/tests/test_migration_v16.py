"""v1.6 数据库迁移测试——NFR-601"""
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base
from app.models.quotation import Quotation, QuotationItem, QuotationChange
from app.models.contract import Contract
from app.models.user import User
from app.core.security import get_password_hash
from app.database import get_db
from app.main import app

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

TEST_DB = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def db_session():
    engine = create_async_engine(TEST_DB, echo=False, poolclass=StaticPool)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        admin = User(
            username="admin", hashed_password=get_password_hash("admin123"),
            full_name="管理员", email="admin@test.com", is_active=True, is_superuser=True,
        )
        session.add(admin)
        await session.commit()
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


class TestMigrationV16:
    """NFR-601: 迁移后验证测试。"""

    @pytest.mark.asyncio
    async def test_all_new_tables_exist(self, db_session: AsyncSession):
        result = await db_session.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name IN ('quotations','quotation_items','quotation_changes')"
        ))
        tables = {row[0] for row in result.fetchall()}
        assert "quotations" in tables
        assert "quotation_items" in tables
        assert "quotation_changes" in tables

    @pytest.mark.asyncio
    async def test_foreign_key_quotation_customer_exists(self, db_session: AsyncSession):
        result = await db_session.execute(text("PRAGMA foreign_key_list(quotations)"))
        fks = result.fetchall()
        fk_tables = {fk[2] for fk in fks}
        assert "customers" in fk_tables

    @pytest.mark.asyncio
    async def test_foreign_key_quotation_project_exists(self, db_session: AsyncSession):
        result = await db_session.execute(text("PRAGMA foreign_key_list(quotations)"))
        fks = result.fetchall()
        fk_tables = {fk[2] for fk in fks}
        assert "projects" in fk_tables

    @pytest.mark.asyncio
    async def test_foreign_key_quotation_item_references_quotations(self, db_session: AsyncSession):
        result = await db_session.execute(text("PRAGMA foreign_key_list(quotation_items)"))
        fks = result.fetchall()
        fk_tables = {fk[2] for fk in fks}
        assert "quotations" in fk_tables

    @pytest.mark.asyncio
    async def test_contracts_quotation_id_exists(self, db_session: AsyncSession):
        result = await db_session.execute(text("PRAGMA table_info(contracts)"))
        columns = {row[1] for row in result.fetchall()}
        assert "quotation_id" in columns

    @pytest.mark.asyncio
    async def test_quotation_table_columns(self, db_session: AsyncSession):
        result = await db_session.execute(text("PRAGMA table_info(quotations)"))
        columns = {row[1] for row in result.fetchall()}
        required_cols = {
            "quote_no", "customer_id", "project_id", "title",
            "requirement_summary", "estimate_days", "estimate_hours",
            "daily_rate", "direct_cost", "risk_buffer_rate",
            "discount_amount", "tax_rate", "subtotal_amount",
            "tax_amount", "total_amount", "valid_until", "status",
            "notes", "sent_at", "accepted_at", "rejected_at",
            "expired_at", "converted_contract_id",
        }
        for col in required_cols:
            assert col in columns, f"缺少字段: {col}"
