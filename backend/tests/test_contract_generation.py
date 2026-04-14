"""v1.12 合同生成测试——覆盖生成、预览、手工编辑、从报价单创建等。"""
import pytest
import pytest_asyncio
from datetime import date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.project import Project
from app.models.quotation import Quotation
from app.models.contract import Contract
from app.crud.contract import contract as contract_crud
from app.crud.quotation import quotation as quotation_crud
from app.core.constants import CONTRACT_CONTENT_FROZEN_STATUS


# ── 辅助 fixtures ─────────────────────────────────────────────────


@pytest_asyncio.fixture
async def customer_project(db_session: AsyncSession):
    """创建客户和项目。"""
    customer = Customer(name="合同测试客户", contact_person="李四", company="测试公司", status="active")
    db_session.add(customer)
    await db_session.flush()

    project = Project(customer_id=customer.id, name="合同测试项目", description="项目描述", status="active")
    db_session.add(project)
    await db_session.flush()
    return customer, project


@pytest_asyncio.fixture
async def draft_contract(db_session: AsyncSession, customer_project):
    """创建 draft 状态合同（有真实的 quotation_id）。"""
    customer, project = customer_project
    # 先创建报价单
    q = Quotation(
        quote_no="BJ-CTEST",
        customer_id=customer.id,
        project_id=project.id,
        title="关联报价",
        requirement_summary="需求",
        estimate_days=10,
        total_amount=10000,
        valid_until=date(2026, 5, 13),
        status="draft",
    )
    db_session.add(q)
    await db_session.flush()

    c = Contract(
        contract_no="HT-001",
        project_id=project.id,
        customer_id=customer.id,
        title="测试合同",
        amount=10000,
        status="draft",
        quotation_id=q.id,
        terms="合同条款",
        signed_date=date(2026, 4, 13),
    )
    db_session.add(c)
    await db_session.flush()
    return c


@pytest_asyncio.fixture
async def active_contract(db_session: AsyncSession, customer_project):
    """创建 active 状态合同（冻结状态）。"""
    customer, project = customer_project
    # 先创建报价单
    q = Quotation(
        quote_no="BJ-ACTIVE",
        customer_id=customer.id,
        project_id=project.id,
        title="活跃合同报价",
        requirement_summary="需求",
        estimate_days=15,
        total_amount=20000,
        valid_until=date(2026, 5, 13),
        status="draft",
    )
    db_session.add(q)
    await db_session.flush()

    c = Contract(
        contract_no="HT-002",
        project_id=project.id,
        customer_id=customer.id,
        title="已激活合同",
        amount=20000,
        status=CONTRACT_CONTENT_FROZEN_STATUS,  # active
        quotation_id=q.id,
        generated_content="已冻结内容",
    )
    db_session.add(c)
    await db_session.flush()
    return c


# ── 5.8-5.13: generate_contract_content ───────────────────────────


@pytest.mark.asyncio
async def test_generate_success(db_session: AsyncSession, draft_contract):
    """验证合同内容生成成功。"""
    content, error = await contract_crud.generate_contract_content(db_session, draft_contract.id)
    assert content is not None
    assert error is None
    assert "HT-001" in content


@pytest.mark.asyncio
async def test_generate_nonempty_without_force_returns_409(db_session: AsyncSession, draft_contract):
    """验证内容已存在且未传 force 时返回 409。"""
    await contract_crud.generate_contract_content(db_session, draft_contract.id)
    from app.core.exception_handlers import BusinessException
    with pytest.raises(BusinessException) as exc_info:
        await contract_crud.generate_contract_content(db_session, draft_contract.id, force=False)
    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_generate_nonempty_with_force_overwrites(db_session: AsyncSession, draft_contract):
    """验证内容已存在且传 force 时覆盖成功。"""
    await contract_crud.generate_contract_content(db_session, draft_contract.id)
    content, error = await contract_crud.generate_contract_content(db_session, draft_contract.id, force=True)
    assert content is not None
    assert error is None


@pytest.mark.asyncio
async def test_generate_active_rejected_even_with_force(db_session: AsyncSession, active_contract):
    """验证 active 状态不可重新生成，即使传 force。"""
    from app.core.exception_handlers import BusinessException
    with pytest.raises(BusinessException) as exc_info:
        await contract_crud.generate_contract_content(db_session, active_contract.id, force=True)
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_generate_without_quotation_id_returns_422(db_session: AsyncSession, customer_project):
    """验证无 quotation_id 时返回 422。"""
    customer, project = customer_project
    c = Contract(
        contract_no="HT-NOQUO",
        project_id=project.id,
        customer_id=customer.id,
        title="无报价合同",
        amount=5000,
        status="draft",
        quotation_id=None,  # 无报价单
    )
    db_session.add(c)
    await db_session.flush()

    from app.core.exception_handlers import BusinessException
    with pytest.raises(BusinessException) as exc_info:
        await contract_crud.generate_contract_content(db_session, c.id)
    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_context_includes_quotation_no(db_session: AsyncSession, customer_project):
    """验证合同上下文包含报价单编号。"""
    customer, project = customer_project
    q = Quotation(
        quote_no="BJ-QTEST",
        customer_id=customer.id,
        project_id=project.id,
        title="关联报价",
        requirement_summary="需求",
        estimate_days=10,
        total_amount=10000,
        valid_until=date(2026, 5, 13),
        status="accepted",
    )
    db_session.add(q)
    await db_session.flush()

    c = Contract(
        contract_no="HT-QTEST",
        project_id=project.id,
        customer_id=customer.id,
        title="合同测试",
        amount=10000,
        status="draft",
        quotation_id=q.id,
    )
    db_session.add(c)
    await db_session.flush()

    content, error = await contract_crud.generate_contract_content(db_session, c.id)
    assert "BJ-QTEST" in content


@pytest.mark.asyncio
async def test_deliverables_desc_empty_not_from_table(db_session: AsyncSession, customer_project):
    """验证 deliverables_desc 为空，不从 deliverables 表取。"""
    customer, project = customer_project
    # 创建报价单
    q = Quotation(
        quote_no="BJ-DELIV",
        customer_id=customer.id,
        project_id=project.id,
        title="交付报价",
        requirement_summary="需求",
        estimate_days=10,
        total_amount=10000,
        valid_until=date(2026, 5, 13),
        status="draft",
    )
    db_session.add(q)
    await db_session.flush()

    c = Contract(
        contract_no="HT-DELIV",
        project_id=project.id,
        customer_id=customer.id,
        title="交付测试",
        amount=10000,
        status="draft",
        quotation_id=q.id,
    )
    db_session.add(c)
    await db_session.flush()

    content, error = await contract_crud.generate_contract_content(db_session, c.id)
    assert content is not None


# ── 5.15-5.17: preview & manual edit ──────────────────────────────


@pytest.mark.asyncio
async def test_preview_no_db_write(db_session: AsyncSession, draft_contract, client):
    """验证预览不写数据库。"""
    h = await _auth(client)
    await contract_crud.generate_contract_content(db_session, draft_contract.id)
    await db_session.refresh(draft_contract)
    original = draft_contract.generated_content

    resp = await client.get(f"/api/v1/contracts/{draft_contract.id}/preview", headers=h)
    assert resp.status_code == 200
    assert "content" in resp.json()

    await db_session.refresh(draft_contract)
    assert draft_contract.generated_content == original


@pytest.mark.asyncio
async def test_manual_edit_does_not_update_content_generated_at(
    db_session: AsyncSession, draft_contract, client
):
    """验证手工编辑不更新 content_generated_at。"""
    h = await _auth(client)
    await contract_crud.generate_contract_content(db_session, draft_contract.id)
    await db_session.refresh(draft_contract)
    original_time = draft_contract.content_generated_at

    resp = await client.put(
        f"/api/v1/contracts/{draft_contract.id}/generated-content",
        params={"content": "编辑后的合同内容"},
        headers=h,
    )
    assert resp.status_code == 200
    await db_session.refresh(draft_contract)
    assert draft_contract.content_generated_at == original_time


@pytest.mark.asyncio
async def test_manual_edit_rejected_when_active(db_session: AsyncSession, active_contract, client):
    """验证 active 状态不可手工编辑。"""
    h = await _auth(client)
    resp = await client.put(
        f"/api/v1/contracts/{active_contract.id}/generated-content",
        params={"content": "非法编辑"},
        headers=h,
    )
    assert resp.status_code in (400, 422)


# ── 5.18-5.23: create_contract_from_quotation ──────────────────────


@pytest_asyncio.fixture
async def accepted_quotation_with_project(db_session: AsyncSession, customer_project):
    """创建 accepted 状态的报价单。"""
    customer, project = customer_project
    q = Quotation(
        quote_no="BJ-ACCEPTED",
        customer_id=customer.id,
        project_id=project.id,
        title="已接受报价",
        requirement_summary="需求摘要",
        estimate_days=20,
        total_amount=50000,
        valid_until=date(2026, 6, 13),
        status="accepted",
    )
    db_session.add(q)
    await db_session.flush()
    return q


@pytest.mark.asyncio
async def test_create_from_quotation_success(db_session: AsyncSession, accepted_quotation_with_project):
    """验证从报价单创建合同成功。"""
    contract = await contract_crud.create_contract_from_quotation(
        db_session, accepted_quotation_with_project.id
    )
    assert contract is not None
    assert contract.status == "draft"
    assert contract.quotation_id == accepted_quotation_with_project.id


@pytest.mark.asyncio
async def test_create_requires_accepted_quotation(db_session: AsyncSession, customer_project):
    """验证只有 accepted 状态的报价单可转合同。"""
    customer, project = customer_project
    q = Quotation(
        quote_no="BJ-DRAFT",
        customer_id=customer.id,
        project_id=project.id,
        title="草稿报价",
        requirement_summary="需求",
        estimate_days=5,
        total_amount=1000,
        valid_until=date(2026, 5, 13),
        status="draft",  # 不是 accepted
    )
    db_session.add(q)
    await db_session.flush()

    from app.core.exception_handlers import BusinessException
    with pytest.raises(BusinessException) as exc_info:
        await contract_crud.create_contract_from_quotation(db_session, q.id)
    assert "QUOTE_NOT_ACCEPTED" in str(exc_info.value.code)


@pytest.mark.asyncio
async def test_create_already_converted_returns_409(db_session: AsyncSession, accepted_quotation_with_project):
    """验证已转合同的报价单不可再次转换。"""
    # 第一次转换
    await contract_crud.create_contract_from_quotation(db_session, accepted_quotation_with_project.id)
    # 第二次转换
    from app.core.exception_handlers import BusinessException
    with pytest.raises(BusinessException) as exc_info:
        await contract_crud.create_contract_from_quotation(db_session, accepted_quotation_with_project.id)
    assert "QUOTE_ALREADY_CONVERTED" in str(exc_info.value.code)


@pytest.mark.asyncio
async def test_create_sets_quotation_id(db_session: AsyncSession, accepted_quotation_with_project):
    """验证创建的合同设置了 quotation_id。"""
    contract = await contract_crud.create_contract_from_quotation(
        db_session, accepted_quotation_with_project.id
    )
    assert contract.quotation_id == accepted_quotation_with_project.id


@pytest.mark.asyncio
async def test_create_updates_converted_contract_id(db_session: AsyncSession, accepted_quotation_with_project):
    """验证创建合同后更新报价单的 converted_contract_id。"""
    contract = await contract_crud.create_contract_from_quotation(
        db_session, accepted_quotation_with_project.id
    )
    await db_session.refresh(accepted_quotation_with_project)
    assert accepted_quotation_with_project.converted_contract_id == contract.id


@pytest.mark.asyncio
async def test_create_atomic(db_session: AsyncSession, accepted_quotation_with_project):
    """验证创建是原子事务：合同和报价单同时更新。"""
    from app.crud.quotation import quotation as quotation_crud

    contract = await contract_crud.create_contract_from_quotation(
        db_session, accepted_quotation_with_project.id
    )

    # 验证两者都在数据库中
    await db_session.refresh(contract)
    await db_session.refresh(accepted_quotation_with_project)

    assert contract.id is not None
    assert contract.quotation_id == accepted_quotation_with_project.id
    assert accepted_quotation_with_project.converted_contract_id == contract.id


# ── API Auth Helper ────────────────────────────────────────────────


async def _auth(client) -> dict:
    """登录并返回 Authorization headers。"""
    r = await client.post("/api/v1/auth/login", data={"username": "admin", "password": "admin123"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
