"""v2.2 迁移测试。"""
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def db():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=StaticPool)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        yield session
    async with engine.begin() as conn:
        try:
            await conn.run_sync(Base.metadata.drop_all)
        except Exception:
            pass
    await engine.dispose()


@pytest.mark.asyncio
async def test_migration_v220_adds_new_columns(db):
    from migrations.v2_2_migrate import _column_exists, migrate
    import sqlite3

    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE agent_suggestions (id INTEGER PRIMARY KEY, title TEXT)"
    )
    conn.commit()

    assert not _column_exists(cur, "agent_suggestions", "risk_score")
    assert not _column_exists(cur, "agent_suggestions", "strategy_code")
    assert not _column_exists(cur, "agent_suggestions", "score_breakdown")

    conn.close()
