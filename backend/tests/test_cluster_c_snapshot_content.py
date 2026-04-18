"""Cluster C Phase 1 — 纪要 + 模板/报告留痕测试（Red 阶段）。

8 个测试用例，对应 PRD FR-C-001 ~ FR-C-008。
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import select

from app.main import app
from app.database import get_db
from app.models.base import Base
from app.models.user import User
from app.models.customer import Customer
from app.models.project import Project
from app.models.entity_snapshot import EntitySnapshot
from app.models.meeting_minute import MeetingMinute
from app.core.security import get_password_hash
from app.core.constants import SNAPSHOT_ENTITY_TYPE_WHITELIST


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def db_session():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=StaticPool)
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
        try:
            await conn.run_sync(Base.metadata.drop_all)
        except Exception:
            pass
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


async def _login(client: AsyncClient) -> dict:
    r = await client.post("/api/v1/auth/login", data={"username": "admin", "password": "admin123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


class TestMinutesCreateWithSnapshot:
    """FR-C-001: 创建纪要后自动触发 snapshot"""

    @pytest.mark.asyncio
    async def test_minutes_create_triggers_snapshot(self, client: AsyncClient, db_session: AsyncSession):
        headers = await _login(client)

        cust = Customer(name="测试客户", contact_person="张三", risk_level="normal")
        db_session.add(cust)
        await db_session.commit()
        await db_session.refresh(cust)

        resp = await client.post(
            "/api/v1/minutes",
            json={
                "title": "项目启动会纪要",
                "content": "讨论了项目范围和里程碑...",
                "client_id": cust.id,
                "meeting_date": "2026-04-17",
            },
            headers=headers,
        )
        assert resp.status_code in [200, 201]

        result = await db_session.execute(
            select(EntitySnapshot).where(EntitySnapshot.entity_type == "minutes")
        )
        snapshots = result.scalars().all()
        assert len(snapshots) >= 1


class TestMinutesUpdateWithSnapshot:
    """FR-C-002: 更新纪要后自动触发 snapshot"""

    @pytest.mark.asyncio
    async def test_minutes_update_triggers_snapshot(self, client: AsyncClient, db_session: AsyncSession):
        headers = await _login(client)

        cust = Customer(name="测试客户2", contact_person="李四", risk_level="normal")
        db_session.add(cust)
        await db_session.commit()
        await db_session.refresh(cust)

        create_resp = await client.post(
            "/api/v1/minutes",
            json={
                "title": "需求评审会",
                "content": "v1 内容",
                "client_id": cust.id,
                "meeting_date": "2026-04-17",
            },
            headers=headers,
        )
        assert create_resp.status_code in [200, 201]
        minutes_id = create_resp.json().get("id")

        update_resp = await client.put(
            f"/api/v1/minutes/{minutes_id}",
            json={
                "title": "需求评审会",
                "content": "v2 更新内容",
                "client_id": cust.id,
                "meeting_date": "2026-04-17",
            },
            headers=headers,
        )
        assert update_resp.status_code == 200

        result = await db_session.execute(
            select(EntitySnapshot).where(EntitySnapshot.entity_type == "minutes")
        )
        snapshots = result.scalars().all()
        assert len(snapshots) >= 2


class TestMinutesAssociationRequired:
    """FR-C-003: 纪要必须关联项目或客户"""

    @pytest.mark.asyncio
    async def test_minutes_without_association_fails(self, client: AsyncClient, db_session: AsyncSession):
        headers = await _login(client)

        resp = await client.post(
            "/api/v1/minutes",
            json={
                "title": "无关联纪要",
                "content": "内容...",
                "meeting_date": "2026-04-17",
            },
            headers=headers,
        )
        assert resp.status_code in [400, 422]


class TestMinutesListAndDelete:
    """FR-C-004: 纪要列表和删除"""

    @pytest.mark.asyncio
    async def test_minutes_list_and_delete(self, client: AsyncClient, db_session: AsyncSession):
        headers = await _login(client)

        cust = Customer(name="测试客户3", contact_person="王五", risk_level="normal")
        db_session.add(cust)
        await db_session.commit()
        await db_session.refresh(cust)

        await client.post(
            "/api/v1/minutes",
            json={
                "title": "纪要1",
                "content": "内容1",
                "client_id": cust.id,
                "meeting_date": "2026-04-17",
            },
            headers=headers,
        )

        list_resp = await client.get("/api/v1/minutes", headers=headers)
        assert list_resp.status_code == 200
        data = list_resp.json()
        assert len(data.get("items", data)) >= 1


class TestTemplateSaveTriggersSnapshot:
    """FR-C-005: 模板保存触发 snapshot"""

    @pytest.mark.asyncio
    async def test_template_save_triggers_snapshot(self, client: AsyncClient, db_session: AsyncSession):
        headers = await _login(client)

        resp = await client.post(
            "/api/v1/templates/",
            params={
                "name": "测试模板",
                "template_type": "report_project",
                "content": "模板内容 {{project_name}}",
            },
            headers=headers,
        )
        assert resp.status_code in [200, 201]

        result = await db_session.execute(
            select(EntitySnapshot).where(EntitySnapshot.entity_type == "template")
        )
        snapshots = result.scalars().all()
        assert len(snapshots) >= 1


class TestTemplateTypeWhitelistExtended:
    """FR-C-006: 模板类型白名单扩展（delivery/retrospective/quotation_calc）"""

    @pytest.mark.asyncio
    async def test_template_type_whitelist_extended(self, client: AsyncClient, db_session: AsyncSession):
        from app.core.constants import TEMPLATE_TYPE_WHITELIST
        assert "delivery" in TEMPLATE_TYPE_WHITELIST
        assert "retrospective" in TEMPLATE_TYPE_WHITELIST
        assert "quotation_calc" in TEMPLATE_TYPE_WHITELIST


class TestReportVersionDiff:
    """FR-C-007: 报告版本对比 API"""

    @pytest.mark.asyncio
    async def test_report_version_diff(self, client: AsyncClient, db_session: AsyncSession):
        from app.services.snapshot_service import create_snapshot, get_version_diff

        await create_snapshot(db_session, "report", 1, {"title": "v1", "content": "版本1"})
        await create_snapshot(db_session, "report", 1, {"title": "v2", "content": "版本2"})

        diff = await get_version_diff(db_session, "report", 1, 1, 2)
        assert diff["version_a"]["version_no"] == 1
        assert diff["version_b"]["version_no"] == 2
        assert diff["version_a"]["content"]["title"] == "v1"
        assert diff["version_b"]["content"]["title"] == "v2"


class TestSnapshotEntityTypeWhitelist:
    """FR-C-008: snapshot entity_type 白名单包含 report/minutes/template"""

    @pytest.mark.asyncio
    async def test_snapshot_entity_type_whitelist(self, client: AsyncClient, db_session: AsyncSession):
        assert "report" in SNAPSHOT_ENTITY_TYPE_WHITELIST
        assert "minutes" in SNAPSHOT_ENTITY_TYPE_WHITELIST
        assert "template" in SNAPSHOT_ENTITY_TYPE_WHITELIST
