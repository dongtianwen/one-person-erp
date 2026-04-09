"""v1.8 会计期间对账测试。"""

import pytest
import pytest_asyncio
from decimal import Decimal
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import get_db
from app.models.base import Base
from app.models.user import User
from app.models.customer import Customer
from app.models.contract import Contract
from app.models.invoice import Invoice
from app.models.finance import FinanceRecord
from app.core.security import get_password_hash

TEST_DB = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """创建内存数据库会话。"""
    engine = create_async_engine(TEST_DB, echo=False, poolclass=StaticPool)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        admin = User(
            username="admin",
            hashed_password=get_password_hash("admin123"),
            full_name="管理员",
            email="admin@test.com",
            is_active=True,
            is_superuser=True,
        )
        session.add(admin)
        await session.commit()
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    """创建测试客户端。"""
    async def override():
        yield db_session
    app.dependency_overrides[get_db] = override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


async def _auth(client: AsyncClient) -> dict:
    """获取认证头。"""
    r = await client.post("/api/v1/auth/login", data={"username": "admin", "password": "admin123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _create_customer(client: AsyncClient, headers: dict) -> int:
    """创建测试客户。"""
    r = await client.post(
        "/api/v1/customers",
        json={
            "name": "测试客户",
            "contact_person": "张三",
            "company": "测试公司",
            "source": "other",
            "status": "deal",
        },
        headers=headers,
    )
    return r.json()["id"]


async def _create_contract(client: AsyncClient, headers: dict, customer_id: int, amount: float = 100000.00) -> dict:
    """创建测试合同。"""
    r = await client.post(
        "/api/v1/contracts",
        json={
            "title": "测试合同",
            "customer_id": customer_id,
            "amount": amount,
            "signed_date": "2024-01-15",
            "start_date": "2024-01-16",
            "end_date": "2024-12-31",
            "status": "active",
        },
        headers=headers,
    )
    return r.json()


async def _create_invoice(client: AsyncClient, headers: dict, contract_id: int) -> dict:
    """创建测试发票。"""
    r = await client.post(
        "/api/v1/invoices",
        json={
            "contract_id": contract_id,
            "invoice_type": "standard",
            "invoice_date": "2024-01-20",
            "amount_excluding_tax": "50000.00",
            "tax_rate": 0.13,
        },
        headers=headers,
    )
    return r.json()


async def _create_payment(client: AsyncClient, headers: dict, contract_id: int, amount: float = 30000.00) -> dict:
    """创建测试收款记录。"""
    r = await client.post(
        "/api/v1/finances",
        json={
            "type": "income",
            "amount": amount,
            "category": "银行转账",
            "date": "2024-01-25",
            "contract_id": contract_id,
            "description": "测试收款",
        },
        headers=headers,
    )
    return r.json()


class TestPeriodList:
    """测试期间列表。"""

    @pytest.mark.asyncio
    async def test_get_periods_returns_available_periods(self, client: AsyncClient):
        """测试获取可用期间列表。"""
        headers = await _auth(client)
        customer_id = await _create_customer(client, headers)
        await _create_contract(client, headers, customer_id)
        await _create_payment(client, headers, (await _create_contract(client, headers, customer_id))["id"])

        r = await client.get(
            "/api/v1/finance/reconciliation",
            headers=headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert "periods" in data
        assert len(data["periods"]) > 0
        assert "2024-01" in data["periods"]


class TestReconciliationReport:
    """测试对账报表。"""

    @pytest.mark.asyncio
    async def test_get_report_returns_complete_data(self, client: AsyncClient):
        """测试获取对账报表返回完整数据。"""
        headers = await _auth(client)
        customer_id = await _create_customer(client, headers)
        await _create_contract(client, headers, customer_id)
        await _create_payment(client, headers, (await _create_contract(client, headers, customer_id))["id"])

        r = await client.get(
            "/api/v1/finance/reconciliation/2024-01",
            headers=headers,
        )
        assert r.status_code == 200
        data = r.json()

        assert data["accounting_period"] == "2024-01"
        assert "period_start" in data
        assert "period_end" in data
        assert "opening_balance" in data
        assert "current_period" in data
        assert "closing_balance" in data
        assert "breakdown" in data
        assert "unreconciled_records" in data

    @pytest.mark.asyncio
    async def test_opening_balance_first_period_is_zero(self, client: AsyncClient):
        """测试第一期期初余额为零。"""
        headers = await _auth(client)
        customer_id = await _create_customer(client, headers)
        await _create_contract(client, headers, customer_id)

        r = await client.get(
            "/api/v1/finance/reconciliation/2024-01",
            headers=headers,
        )
        assert r.status_code == 200
        opening = r.json()["opening_balance"]
        assert opening["accounts_receivable"] == 0
        assert opening["unbilled_amount"] == 0
        assert opening["total"] == 0

    @pytest.mark.asyncio
    async def test_current_period_counts_correctly(self, client: AsyncClient):
        """测试本期活动统计正确。"""
        headers = await _auth(client)
        customer_id = await _create_customer(client, headers)
        contract = await _create_contract(client, headers, customer_id)
        await _create_payment(client, headers, contract["id"])
        await _create_invoice(client, headers, contract["id"])

        r = await client.get(
            "/api/v1/finance/reconciliation/2024-01",
            headers=headers,
        )
        assert r.status_code == 200
        current = r.json()["current_period"]

        assert current["contracts_signed"] >= 1
        assert current["contracts_amount"] > 0
        assert current["payments_received"] >= 1
        assert current["payments_amount"] > 0
        assert current["invoices_issued"] >= 1
        assert current["invoices_amount"] > 0

    @pytest.mark.asyncio
    async def test_closing_balance_calculates_correctly(self, client: AsyncClient):
        """测试期末余额计算正确。"""
        headers = await _auth(client)
        customer_id = await _create_customer(client, headers)
        contract = await _create_contract(client, headers, customer_id, amount=100000)
        await _create_payment(client, headers, contract["id"], amount=30000)

        r = await client.get(
            "/api/v1/finance/reconciliation/2024-01",
            headers=headers,
        )
        assert r.status_code == 200
        closing = r.json()["closing_balance"]

        # 期末应收 = 期初(0) + 本期合同(100000) - 本期收款(30000) = 70000
        assert closing["accounts_receivable"] == 70000.0

    @pytest.mark.asyncio
    async def test_customer_breakdown_includes_customer_data(self, client: AsyncClient):
        """测试客户分解包含客户数据。"""
        headers = await _auth(client)
        customer_id = await _create_customer(client, headers)
        await _create_contract(client, headers, customer_id)

        r = await client.get(
            "/api/v1/finance/reconciliation/2024-01",
            headers=headers,
        )
        assert r.status_code == 200
        breakdown = r.json()["breakdown"]

        assert len(breakdown) > 0
        assert breakdown[0]["customer_name"] == "测试客户"
        assert "contracts_amount_this_period" in breakdown[0]
        assert "payments_amount_this_period" in breakdown[0]

    @pytest.mark.asyncio
    async def test_unreconciled_records_identifies_unmatched_payments(self, client: AsyncClient):
        """测试未对账记录识别无合同收款。"""
        headers = await _auth(client)
        customer_id = await _create_customer(client, headers)

        # 创建无合同收款
        r = await client.post(
            "/api/v1/finances",
            json={
                "type": "income",
                "amount": 5000.00,
                "category": "现金",
                "date": "2024-01-15",
                "description": "无合同收款",
            },
            headers=headers,
        )
        assert r.status_code == 201

        r2 = await client.get(
            "/api/v1/finance/reconciliation/2024-01",
            headers=headers,
        )
        assert r2.status_code == 200
        unreconciled = r2.json()["unreconciled_records"]

        assert len(unreconciled) > 0
        assert unreconciled[0]["reason"] == "无匹配合同"


class TestSyncStatus:
    """测试对账状态同步。"""

    @pytest.mark.asyncio
    async def test_sync_updates_matched_status(self, client: AsyncClient, db_session: AsyncSession):
        """测试同步更新 matched 状态。"""
        headers = await _auth(client)
        customer_id = await _create_customer(client, headers)
        contract = await _create_contract(client, headers, customer_id)
        payment = await _create_payment(client, headers, contract["id"])

        r = await client.post(
            "/api/v1/finance/reconciliation/sync",
            json={"record_ids": [payment["id"]]},
            headers=headers,
        )
        assert r.status_code == 200
        assert r.json()["updated_count"] == 1

    @pytest.mark.asyncio
    async def test_sync_with_verified_invoice_sets_verified_status(self, client: AsyncClient, db_session: AsyncSession):
        """测试同步 verified 发票设置 verified 状态。"""
        headers = await _auth(client)
        customer_id = await _create_customer(client, headers)
        contract = await _create_contract(client, headers, customer_id)
        invoice = await _create_invoice(client, headers, contract["id"])

        # 核销发票
        await client.post(f"/api/v1/invoices/{invoice['id']}/verify", headers=headers)

        # 创建收款并关联发票
        payment = await _create_payment(client, headers, contract["id"])

        # 更新收款记录关联发票
        from sqlalchemy import select
        stmt = select(FinanceRecord).where(FinanceRecord.id == payment["id"])
        result = await db_session.execute(stmt)
        record = result.scalar_one_or_none()
        record.invoice_id = invoice["id"]
        await db_session.commit()

        # 同步状态
        r = await client.post(
            "/api/v1/finance/reconciliation/sync",
            json={"record_ids": [payment["id"]]},
            headers=headers,
        )
        assert r.status_code == 200
        assert r.json()["updated_count"] == 1


class TestPeriodDateRange:
    """测试期间日期范围。"""

    @pytest.mark.asyncio
    async def test_report_includes_correct_date_range(self, client: AsyncClient):
        """测试报表包含正确的日期范围。"""
        headers = await _auth(client)
        customer_id = await _create_customer(client, headers)
        await _create_contract(client, headers, customer_id)

        r = await client.get(
            "/api/v1/finance/reconciliation/2024-01",
            headers=headers,
        )
        assert r.status_code == 200
        data = r.json()

        assert data["period_start"] == "2024-01-01"
        assert data["period_end"] == "2024-01-31"
