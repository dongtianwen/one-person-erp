"""v1.12 报价单生成测试——覆盖生成、预览、手工编辑、从项目创建等。"""
import json
import pytest
import pytest_asyncio
from datetime import date, datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.project import Project
from app.models.quotation import Quotation
from app.models.template import Template
from app.crud.quotation import quotation as quotation_crud
from app.core.constants import QUOTATION_CONTENT_FROZEN_STATUS, QUOTATION_REQUIRED_VARS


# ── 辅助函数 ──────────────────────────────────────────────────────


async def _auth(client) -> dict:
    """登录并返回 Authorization headers。"""
    r = await client.post("/api/v1/auth/login", data={"username": "admin", "password": "admin123"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest_asyncio.fixture
async def customer_and_project(db_session: AsyncSession):
    """创建客户和项目，返回 (customer, project) 元组。"""
    customer = Customer(
        name="测试客户",
        contact_person="张三",
        company="测试公司",
        status="active",
    )
    db_session.add(customer)
    await db_session.flush()

    project = Project(
        customer_id=customer.id,
        name="测试项目",
        description="项目描述",
        status="active",
    )
    db_session.add(project)
    await db_session.flush()
    return customer, project


@pytest_asyncio.fixture
async def draft_quotation(db_session: AsyncSession, customer_and_project):
    """创建一份 draft 状态的报价单。"""
    customer, project = customer_and_project
    q = Quotation(
        quote_no="BJ-001",
        customer_id=customer.id,
        project_id=project.id,
        title="测试报价",
        requirement_summary="测试需求",
        estimate_days=10,
        total_amount=10000,
        valid_until=date(2026, 5, 13),
        status="draft",
    )
    db_session.add(q)
    await db_session.flush()
    return q


@pytest_asyncio.fixture
async def accepted_quotation(db_session: AsyncSession, customer_and_project):
    """创建一份 accepted 状态的报价单（冻结状态）。"""
    customer, project = customer_and_project
    q = Quotation(
        quote_no="BJ-002",
        customer_id=customer.id,
        project_id=project.id,
        title="已接受报价",
        requirement_summary="已接受需求",
        estimate_days=15,
        total_amount=20000,
        valid_until=date(2026, 5, 13),
        status=QUOTATION_CONTENT_FROZEN_STATUS,  # accepted
        generated_content="已冻结的内容快照",
    )
    db_session.add(q)
    await db_session.flush()
    return q


# ── 4.9-4.14: generate_quotation_content ──────────────────────────


@pytest.mark.asyncio
async def test_generate_content_when_empty(db_session: AsyncSession, draft_quotation):
    """验证内容为空时可以生成。"""
    content, error = await quotation_crud.generate_quotation_content(
        db_session, draft_quotation.id, force=False
    )
    assert content is not None
    assert error is None
    assert "BJ-001" in content


@pytest.mark.asyncio
async def test_generate_writes_snapshot(db_session: AsyncSession, draft_quotation):
    """验证生成后内容写入数据库。"""
    await quotation_crud.generate_quotation_content(db_session, draft_quotation.id)
    await db_session.refresh(draft_quotation)
    assert draft_quotation.generated_content is not None
    assert draft_quotation.content_generated_at is not None
    assert draft_quotation.template_id is not None


@pytest.mark.asyncio
async def test_generate_nonempty_without_force_returns_409(db_session: AsyncSession, draft_quotation):
    """验证内容已存在且未传 force 时返回 409。"""
    # 先生成内容
    await quotation_crud.generate_quotation_content(db_session, draft_quotation.id)
    # 再次生成，不传 force
    from app.core.exception_handlers import BusinessException
    with pytest.raises(BusinessException) as exc_info:
        await quotation_crud.generate_quotation_content(db_session, draft_quotation.id, force=False)
    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_generate_nonempty_with_force_overwrites(db_session: AsyncSession, draft_quotation):
    """验证内容已存在且传 force 时覆盖成功。"""
    await quotation_crud.generate_quotation_content(db_session, draft_quotation.id)
    old_content = draft_quotation.generated_content
    content, error = await quotation_crud.generate_quotation_content(
        db_session, draft_quotation.id, force=True
    )
    assert content is not None
    assert error is None


@pytest.mark.asyncio
async def test_generate_accepted_rejected_even_with_force(db_session: AsyncSession, accepted_quotation):
    """验证 accepted 状态不可重新生成，即使传 force。"""
    from app.core.exception_handlers import BusinessException
    with pytest.raises(BusinessException) as exc_info:
        await quotation_crud.generate_quotation_content(
            db_session, accepted_quotation.id, force=True
        )
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_regenerate_updates_content_generated_at(
    db_session: AsyncSession, draft_quotation
):
    """验证重新生成更新时间戳。"""
    import time
    await quotation_crud.generate_quotation_content(db_session, draft_quotation.id)
    first_time = draft_quotation.content_generated_at
    time.sleep(0.1)
    await quotation_crud.generate_quotation_content(db_session, draft_quotation.id, force=True)
    await db_session.refresh(draft_quotation)
    assert draft_quotation.content_generated_at > first_time


# ── 4.15-4.16: preview ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_preview_no_db_write(db_session: AsyncSession, draft_quotation, client):
    """验证预览不写数据库。"""
    h = await _auth(client)
    await quotation_crud.generate_quotation_content(db_session, draft_quotation.id)
    await db_session.refresh(draft_quotation)
    original_content = draft_quotation.generated_content

    resp = await client.get(f"/api/v1/quotations/{draft_quotation.id}/preview", headers=h)
    assert resp.status_code == 200
    assert "content" in resp.json()

    await db_session.refresh(draft_quotation)
    assert draft_quotation.generated_content == original_content


@pytest.mark.asyncio
async def test_preview_allowed_when_accepted(db_session: AsyncSession, accepted_quotation, client):
    """验证 accepted 状态可以预览。"""
    h = await _auth(client)
    resp = await client.get(f"/api/v1/quotations/{accepted_quotation.id}/preview", headers=h)
    assert resp.status_code == 200
    assert "content" in resp.json()


# ── 4.17-4.18: manual edit ───────────────────────────────────────


@pytest.mark.asyncio
async def test_manual_edit_success(db_session: AsyncSession, draft_quotation, client):
    """验证手工编辑内容成功。"""
    h = await _auth(client)
    await quotation_crud.generate_quotation_content(db_session, draft_quotation.id)

    resp = await client.put(
        f"/api/v1/quotations/{draft_quotation.id}/generated-content",
        params={"content": "手工编辑的新内容"},
        headers=h,
    )
    assert resp.status_code == 200
    await db_session.refresh(draft_quotation)
    assert "手工编辑的新内容" in draft_quotation.generated_content


@pytest.mark.asyncio
async def test_manual_edit_does_not_update_content_generated_at(
    db_session: AsyncSession, draft_quotation, client
):
    """验证手工编辑不更新 content_generated_at。"""
    h = await _auth(client)
    await quotation_crud.generate_quotation_content(db_session, draft_quotation.id)
    await db_session.refresh(draft_quotation)
    original_time = draft_quotation.content_generated_at

    await client.put(
        f"/api/v1/quotations/{draft_quotation.id}/generated-content",
        params={"content": "编辑后的内容"},
        headers=h,
    )
    await db_session.refresh(draft_quotation)
    assert draft_quotation.content_generated_at == original_time


@pytest.mark.asyncio
async def test_manual_edit_rejected_when_accepted(
    db_session: AsyncSession, accepted_quotation, client
):
    """验证 accepted 状态不可手工编辑。"""
    h = await _auth(client)
    resp = await client.put(
        f"/api/v1/quotations/{accepted_quotation.id}/generated-content",
        params={"content": "非法编辑"},
        headers=h,
    )
    assert resp.status_code in (400, 422)


# ── 4.19-4.22: create from project ───────────────────────────────


@pytest.mark.asyncio
async def test_create_from_project_success(db_session: AsyncSession, customer_and_project, client):
    """验证从项目创建报价单成功。"""
    h = await _auth(client)
    _, project = customer_and_project
    resp = await client.post(f"/api/v1/quotations/projects/{project.id}/generate-quotation", headers=h)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "draft"
    assert data["title"] == project.name


@pytest.mark.asyncio
async def test_create_from_project_draft_dedup(db_session: AsyncSession, customer_and_project, client):
    """验证项目已有草稿时返回 409。"""
    h = await _auth(client)
    _, project = customer_and_project
    resp = await client.post(f"/api/v1/quotations/projects/{project.id}/generate-quotation", headers=h)
    assert resp.status_code == 200
    resp = await client.post(f"/api/v1/quotations/projects/{project.id}/generate-quotation", headers=h)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_create_from_project_non_draft_allows_new(db_session: AsyncSession, customer_and_project):
    """验证项目有非 draft 报价单时仍可创建新草稿。"""
    _, project = customer_and_project
    # 创建一份非 draft 的报价单
    q = Quotation(
        quote_no="BJ-EXISTING",
        customer_id=customer_and_project[0].id,
        project_id=project.id,
        title="非草稿报价",
        requirement_summary="需求",
        estimate_days=5,
        total_amount=5000,
        valid_until=date(2026, 5, 13),
        status="sent",  # 非 draft
    )
    db_session.add(q)
    await db_session.flush()

    # 仍然可以创建新的草稿
    new_q = await quotation_crud.create_quotation_from_project(db_session, project.id)
    assert new_q is not None
    assert new_q.status == "draft"
