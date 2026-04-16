"""v2.1 交付/质检智能体测试。"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.core.constants import (
    SUGGESTION_TYPE_DELIVERY_MISSING_MODEL,
    SUGGESTION_TYPE_DELIVERY_MISSING_DATASET,
    SUGGESTION_TYPE_DELIVERY_MISSING_ACCEPTANCE,
    SUGGESTION_TYPE_DELIVERY_VERSION_MISMATCH,
    SUGGESTION_TYPE_DELIVERY_EMPTY_PACKAGE,
    SUGGESTION_TYPE_DELIVERY_UNBOUND_PROJECT,
    AGENT_TYPE_DELIVERY_QC,
)

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


async def _create_project(db):
    from app.models.project import Project
    from app.models.customer import Customer
    customer = Customer(name="测试客户", contact_person="张三")
    db.add(customer)
    await db.flush()
    project = Project(name="测试项目", customer_id=customer.id, budget=100000)
    db.add(project)
    await db.flush()
    return project


def test_delivery_qc_suggestion_types():
    types = [
        SUGGESTION_TYPE_DELIVERY_MISSING_MODEL,
        SUGGESTION_TYPE_DELIVERY_MISSING_DATASET,
        SUGGESTION_TYPE_DELIVERY_MISSING_ACCEPTANCE,
        SUGGESTION_TYPE_DELIVERY_VERSION_MISMATCH,
        SUGGESTION_TYPE_DELIVERY_EMPTY_PACKAGE,
        SUGGESTION_TYPE_DELIVERY_UNBOUND_PROJECT,
    ]
    assert len(types) == 6
    assert len(set(types)) == 6


def test_agent_type_delivery_qc():
    assert AGENT_TYPE_DELIVERY_QC == "delivery_qc"


@pytest.mark.asyncio
async def test_evaluate_delivery_package_not_found(db):
    from app.core.agent_rules import evaluate_delivery_package
    from app.core.exception_handlers import BusinessException

    with pytest.raises(BusinessException) as exc_info:
        await evaluate_delivery_package(db, 99999)
    assert exc_info.value.code == "DELIVERY_QC_NO_PACKAGE"


@pytest.mark.asyncio
async def test_evaluate_delivery_package_all_issues(db):
    from app.core.agent_rules import evaluate_delivery_package
    from app.models.delivery_package import DeliveryPackage

    project = await _create_project(db)
    pkg = DeliveryPackage(
        name="空交付包",
        status="draft",
        project_id=project.id,
    )
    db.add(pkg)
    await db.commit()

    with patch("app.core.agent_rules._has_model_version", return_value=False), \
         patch("app.core.agent_rules._has_dataset_version", return_value=False), \
         patch("app.core.agent_rules._has_acceptance_record", return_value=False), \
         patch("app.core.agent_rules._has_deprecated_model", return_value=False), \
         patch("app.core.agent_rules._is_empty_package", return_value=True):
        suggestions = await evaluate_delivery_package(db, pkg.id)

    types = [s["suggestion_type"] for s in suggestions]
    assert SUGGESTION_TYPE_DELIVERY_MISSING_MODEL in types
    assert SUGGESTION_TYPE_DELIVERY_MISSING_DATASET in types
    assert SUGGESTION_TYPE_DELIVERY_MISSING_ACCEPTANCE in types
    assert SUGGESTION_TYPE_DELIVERY_EMPTY_PACKAGE in types


@pytest.mark.asyncio
async def test_evaluate_delivery_package_unbound_project(db):
    from app.core.agent_rules import evaluate_delivery_package
    from app.models.delivery_package import DeliveryPackage

    project = await _create_project(db)
    pkg = DeliveryPackage(
        name="未绑定项目包",
        status="draft",
        project_id=project.id,
    )
    db.add(pkg)
    await db.commit()

    with patch("app.core.agent_rules._has_model_version", return_value=True), \
         patch("app.core.agent_rules._has_dataset_version", return_value=True), \
         patch("app.core.agent_rules._has_acceptance_record", return_value=True), \
         patch("app.core.agent_rules._has_deprecated_model", return_value=False), \
         patch("app.core.agent_rules._is_empty_package", return_value=False):
        suggestions = await evaluate_delivery_package(db, pkg.id)

    assert len(suggestions) == 0


@pytest.mark.asyncio
async def test_evaluate_delivery_package_deprecated_model(db):
    from app.core.agent_rules import evaluate_delivery_package
    from app.models.delivery_package import DeliveryPackage

    project = await _create_project(db)
    pkg = DeliveryPackage(
        name="有废弃模型",
        status="accepted",
        project_id=project.id,
    )
    db.add(pkg)
    await db.commit()

    with patch("app.core.agent_rules._has_model_version", return_value=True), \
         patch("app.core.agent_rules._has_dataset_version", return_value=True), \
         patch("app.core.agent_rules._has_acceptance_record", return_value=True), \
         patch("app.core.agent_rules._has_deprecated_model", return_value=True), \
         patch("app.core.agent_rules._is_empty_package", return_value=False):
        suggestions = await evaluate_delivery_package(db, pkg.id)

    types = [s["suggestion_type"] for s in suggestions]
    assert SUGGESTION_TYPE_DELIVERY_VERSION_MISMATCH in types
    assert len(suggestions) == 1


@pytest.mark.asyncio
async def test_evaluate_delivery_package_all_pass(db):
    from app.core.agent_rules import evaluate_delivery_package
    from app.models.delivery_package import DeliveryPackage

    project = await _create_project(db)
    pkg = DeliveryPackage(
        name="完整交付包",
        status="accepted",
        project_id=project.id,
    )
    db.add(pkg)
    await db.commit()

    with patch("app.core.agent_rules._has_model_version", return_value=True), \
         patch("app.core.agent_rules._has_dataset_version", return_value=True), \
         patch("app.core.agent_rules._has_acceptance_record", return_value=True), \
         patch("app.core.agent_rules._has_deprecated_model", return_value=False), \
         patch("app.core.agent_rules._is_empty_package", return_value=False):
        suggestions = await evaluate_delivery_package(db, pkg.id)

    assert len(suggestions) == 0
