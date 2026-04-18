"""Cluster A1 Phase 1 — snapshot 底座测试（Red 阶段）。

7 个测试用例，对应 PRD FR-A1-001 ~ FR-A1-007。
本阶段仅编写测试，不编写任何业务代码，运行后应全部 FAILED。
"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.services.snapshot_service import (
    create_snapshot,
    get_latest_snapshot,
    get_snapshot_history,
    save_with_snapshot,
    get_version_diff,
)
from app.models.entity_snapshot import EntitySnapshot


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def db_session():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=StaticPool)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(EntitySnapshot.metadata.create_all)

    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        try:
            await conn.run_sync(Base.metadata.drop_all)
        except Exception:
            pass

    await engine.dispose()


class TestSnapshotCreate:
    """FR-A1-001: 报告实体快照写入成功，is_latest=True"""

    @pytest.mark.asyncio
    async def test_snapshot_create_report(self, db_session: AsyncSession):
        snapshot_json = {"title": "Q1 项目报告", "content": "报告正文..."}
        success, warning_code = await create_snapshot(
            db=db_session,
            entity_type="report",
            entity_id=1,
            snapshot_json=snapshot_json,
        )
        assert success is True
        assert warning_code is None

        result = await get_latest_snapshot(db_session, "report", 1)
        assert result is not None
        assert result["version_no"] == 1
        assert result["is_latest"] is True
        assert result["snapshot_json"]["title"] == "Q1 项目报告"


class TestSnapshotPreviousNotLatest:
    """FR-A1-002: 新快照写入后，同实体前一版 is_latest 自动置 False"""

    @pytest.mark.asyncio
    async def test_snapshot_create_sets_previous_not_latest(self, db_session: AsyncSession):
        await create_snapshot(db_session, "report", 1, {"title": "v1"})
        await create_snapshot(db_session, "report", 1, {"title": "v2"})

        latest = await get_latest_snapshot(db_session, "report", 1)
        assert latest["version_no"] == 2
        assert latest["is_latest"] is True

        history = await get_snapshot_history(db_session, "report", 1)
        assert len(history) == 2
        v1 = [h for h in history if h["version_no"] == 1][0]
        assert v1["is_latest"] is False


class TestSnapshotVersionIncrements:
    """FR-A1-003: 同一实体多次快照，version_no 单调递增"""

    @pytest.mark.asyncio
    async def test_snapshot_version_increments(self, db_session: AsyncSession):
        for i in range(1, 4):
            await create_snapshot(db_session, "report", 1, {"title": f"v{i}"})

        history = await get_snapshot_history(db_session, "report", 1)
        assert len(history) == 3
        versions = [h["version_no"] for h in history]
        assert versions == [1, 2, 3]


class TestSnapshotPydanticValidation:
    """FR-A1-004: snapshot_json 入库前经过 pydantic 校验，非法结构拒绝写入"""

    @pytest.mark.asyncio
    async def test_snapshot_json_validated_by_pydantic(self, db_session: AsyncSession):
        success, warning_code = await create_snapshot(
            db=db_session,
            entity_type="report",
            entity_id=1,
            snapshot_json="not a dict",
        )
        assert success is False
        assert warning_code == "SNAPSHOT_WRITE_FAILED"


class TestSnapshotWriteFailureReturnsWarning:
    """FR-A1-005: 快照写入失败时，API 返回 success=true + warning_code，主业务未回滚"""

    @pytest.mark.asyncio
    async def test_snapshot_write_failure_returns_warning(self, db_session: AsyncSession):
        main_business_saved = {"id": 99, "title": "主业务数据"}

        async def mock_db_save_fn(db):
            main_business_saved["saved"] = True

        success, warning_code = await save_with_snapshot(
            db=db_session,
            entity_type="report",
            entity_id=99,
            snapshot_json="invalid",
            db_save_fn=mock_db_save_fn,
        )
        assert success is True
        assert warning_code == "SNAPSHOT_WRITE_FAILED"
        assert main_business_saved.get("saved") is True


class TestSnapshotMultipleEntityTypes:
    """FR-A1-006: entity_type 支持 report / minutes / template，查询互不干扰"""

    @pytest.mark.asyncio
    async def test_snapshot_supports_multiple_entity_types(self, db_session: AsyncSession):
        await create_snapshot(db_session, "report", 1, {"title": "报告"})
        await create_snapshot(db_session, "minutes", 1, {"title": "纪要"})
        await create_snapshot(db_session, "template", 1, {"title": "模板"})

        report_latest = await get_latest_snapshot(db_session, "report", 1)
        minutes_latest = await get_latest_snapshot(db_session, "minutes", 1)
        template_latest = await get_latest_snapshot(db_session, "template", 1)

        assert report_latest["snapshot_json"]["title"] == "报告"
        assert minutes_latest["snapshot_json"]["title"] == "纪要"
        assert template_latest["snapshot_json"]["title"] == "模板"

        report_history = await get_snapshot_history(db_session, "report", 1)
        assert len(report_history) == 1


class TestSnapshotParentChain:
    """FR-A1-007: parent_snapshot_id 正确关联上一版本，形成可回溯链"""

    @pytest.mark.asyncio
    async def test_snapshot_parent_chain(self, db_session: AsyncSession):
        await create_snapshot(db_session, "report", 1, {"title": "v1"})
        await create_snapshot(db_session, "report", 1, {"title": "v2"})
        await create_snapshot(db_session, "report", 1, {"title": "v3"})

        history = await get_snapshot_history(db_session, "report", 1)
        assert len(history) == 3

        v1 = [h for h in history if h["version_no"] == 1][0]
        v2 = [h for h in history if h["version_no"] == 2][0]
        v3 = [h for h in history if h["version_no"] == 3][0]

        assert v1["parent_snapshot_id"] is None
        assert v2["parent_snapshot_id"] == v1["id"]
        assert v3["parent_snapshot_id"] == v2["id"]
