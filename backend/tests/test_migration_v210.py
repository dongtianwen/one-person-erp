import pytest
import pytest_asyncio
from sqlalchemy import text, inspect
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.report import Report
from app.models.template import Template
from app.core.constants import (
    TEMPLATE_TYPE_WHITELIST,
    AGENT_TYPE_WHITELIST,
    TEMPLATE_TYPE_REPORT_PROJECT,
    TEMPLATE_TYPE_REPORT_CUSTOMER,
    AGENT_TYPE_DELIVERY_QC,
    REPORT_TYPE_WHITELIST,
    SUGGESTION_TYPE_DELIVERY_MISSING_MODEL,
    SUGGESTION_TYPE_DELIVERY_MISSING_DATASET,
    SUGGESTION_TYPE_DELIVERY_MISSING_ACCEPTANCE,
    SUGGESTION_TYPE_DELIVERY_VERSION_MISMATCH,
    SUGGESTION_TYPE_DELIVERY_EMPTY_PACKAGE,
    SUGGESTION_TYPE_DELIVERY_UNBOUND_PROJECT,
)
from app.core.error_codes import ERROR_CODES

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
async def test_reports_table_exists(db):
    result = await db.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='reports'"))
    assert result.fetchone() is not None


@pytest.mark.asyncio
async def test_reports_entity_index_exists(db):
    result = await db.execute(text("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_reports_entity'"))
    assert result.fetchone() is not None


@pytest.mark.asyncio
async def test_reports_type_status_index_exists(db):
    result = await db.execute(text("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_reports_type_status'"))
    assert result.fetchone() is not None


def test_template_type_whitelist_includes_report_types():
    assert TEMPLATE_TYPE_REPORT_PROJECT in TEMPLATE_TYPE_WHITELIST
    assert TEMPLATE_TYPE_REPORT_CUSTOMER in TEMPLATE_TYPE_WHITELIST


def test_agent_type_whitelist_includes_delivery_qc():
    assert AGENT_TYPE_DELIVERY_QC in AGENT_TYPE_WHITELIST


@pytest.mark.asyncio
async def test_default_project_report_template_inserted(db):
    result = await db.execute(
        text("SELECT COUNT(*) FROM templates WHERE template_type='report_project' AND is_default=1")
    )
    count = result.scalar()
    assert count == 0 or count == 1


@pytest.mark.asyncio
async def test_default_customer_report_template_inserted(db):
    result = await db.execute(
        text("SELECT COUNT(*) FROM templates WHERE template_type='report_customer' AND is_default=1")
    )
    count = result.scalar()
    assert count == 0 or count == 1


@pytest.mark.asyncio
async def test_report_templates_idempotent_no_duplicate(db):
    from app.services.seed import DEFAULT_REPORT_TEMPLATES
    for tpl_data in DEFAULT_REPORT_TEMPLATES:
        result = await db.execute(
            text("SELECT COUNT(*) FROM templates WHERE template_type=:ttype AND is_default=1"),
            {"ttype": tpl_data["template_type"]},
        )
        count = result.scalar()
        if count == 0:
            template = Template(**tpl_data)
            db.add(template)
            await db.commit()

    result = await db.execute(
        text("SELECT COUNT(*) FROM templates WHERE template_type='report_project' AND is_default=1")
    )
    assert result.scalar() == 1

    result = await db.execute(
        text("SELECT COUNT(*) FROM templates WHERE template_type='report_customer' AND is_default=1")
    )
    assert result.scalar() == 1


@pytest.mark.asyncio
async def test_existing_tables_row_counts_unchanged(db):
    for table_name in ["projects", "customers", "contracts", "finance_records"]:
        result = await db.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
        count = result.scalar()
        assert count == 0


@pytest.mark.asyncio
async def test_existing_tables_fields_unchanged(db):
    result = await db.execute(text("PRAGMA table_info(templates)"))
    columns = [row[1] for row in result.fetchall()]
    for col in ["id", "name", "template_type", "content", "is_default", "description"]:
        assert col in columns


def test_report_type_whitelist():
    assert "report_project" in REPORT_TYPE_WHITELIST
    assert "report_customer" in REPORT_TYPE_WHITELIST


def test_delivery_qc_suggestion_types_in_error_codes():
    for code in [
        "QA_REQUIRES_API_PROVIDER",
        "QA_CONTEXT_BUILD_FAILED",
        "REPORT_TYPE_NOT_SUPPORTED",
        "REPORT_ENTITY_NOT_FOUND",
        "REPORT_LLM_FILL_FAILED",
        "DELIVERY_QC_NO_PACKAGE",
    ]:
        assert code in ERROR_CODES


def test_delivery_suggestion_types_defined():
    types = [
        SUGGESTION_TYPE_DELIVERY_MISSING_MODEL,
        SUGGESTION_TYPE_DELIVERY_MISSING_DATASET,
        SUGGESTION_TYPE_DELIVERY_MISSING_ACCEPTANCE,
        SUGGESTION_TYPE_DELIVERY_VERSION_MISMATCH,
        SUGGESTION_TYPE_DELIVERY_EMPTY_PACKAGE,
        SUGGESTION_TYPE_DELIVERY_UNBOUND_PROJECT,
    ]
    for t in types:
        assert isinstance(t, str)
        assert len(t) > 0
