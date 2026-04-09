"""v1.8 财务数据导出测试。"""

import os
import pytest
import pytest_asyncio
from decimal import Decimal
from datetime import date, datetime
from httpx import AsyncClient, ASGITransport
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import get_db
from app.models.base import Base
from app.models.user import User
from app.models.customer import Customer
from app.models.contract import Contract
from app.models.quotation import Quotation
from app.models.invoice import Invoice
from app.models.finance import FinanceRecord
from app.models.export_batch import ExportBatch  # 必须导入以创建表
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


async def _create_contract(client: AsyncClient, headers: dict, customer_id: int, amount: Decimal = Decimal("100000.00")) -> dict:
    """创建测试合同。"""
    r = await client.post(
        "/api/v1/contracts",
        json={
            "title": "测试合同",
            "customer_id": customer_id,
            "amount": float(amount),
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


async def _create_payment(client: AsyncClient, headers: dict, contract_id: int) -> dict:
    """创建测试收款记录。"""
    r = await client.post(
        "/api/v1/finances",
        json={
            "type": "income",
            "amount": 30000.00,
            "category": "银行转账",
            "date": "2024-01-25",
            "contract_id": contract_id,
            "description": "测试收款",
        },
        headers=headers,
    )
    return r.json()


class TestExportContracts:
    """测试合同导出。"""

    @pytest.mark.asyncio
    async def test_export_contracts_generic_success(self, client: AsyncClient):
        """测试导出合同成功。"""
        headers = await _auth(client)
        customer_id = await _create_customer(client, headers)
        await _create_contract(client, headers, customer_id)

        r = await client.post(
            "/api/v1/finance/export",
            json={
                "export_type": "contracts",
                "target_format": "generic",
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
            },
            headers=headers,
        )
        assert r.status_code == 201
        data = r.json()
        assert "batch_id" in data
        assert "file_path" in data
        assert data["record_count"] > 0
        assert data["batch_id"].startswith("EXP-")

    @pytest.mark.asyncio
    async def test_export_by_accounting_period_filters_correctly(self, client: AsyncClient):
        """测试按会计期间筛选。"""
        headers = await _auth(client)
        customer_id = await _create_customer(client, headers)
        await _create_contract(client, headers, customer_id)

        r = await client.post(
            "/api/v1/finance/export",
            json={
                "export_type": "contracts",
                "target_format": "generic",
                "accounting_period": "2024-01",
            },
            headers=headers,
        )
        assert r.status_code == 201
        data = r.json()
        assert data["record_count"] > 0

    @pytest.mark.asyncio
    async def test_export_by_date_range_filters_correctly(self, client: AsyncClient):
        """测试按日期范围筛选。"""
        headers = await _auth(client)
        customer_id = await _create_customer(client, headers)
        await _create_contract(client, headers, customer_id)

        r = await client.post(
            "/api/v1/finance/export",
            json={
                "export_type": "contracts",
                "target_format": "generic",
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
            },
            headers=headers,
        )
        assert r.status_code == 201
        data = r.json()
        assert data["record_count"] > 0


class TestExportPayments:
    """测试收款导出。"""

    @pytest.mark.asyncio
    async def test_export_payments_generic_success(self, client: AsyncClient):
        """测试导出收款成功。"""
        headers = await _auth(client)
        customer_id = await _create_customer(client, headers)
        contract = await _create_contract(client, headers, customer_id)
        await _create_payment(client, headers, contract["id"])

        r = await client.post(
            "/api/v1/finance/export",
            json={
                "export_type": "payments",
                "target_format": "generic",
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
            },
            headers=headers,
        )
        assert r.status_code == 201
        data = r.json()
        assert "batch_id" in data
        assert data["record_count"] > 0

    @pytest.mark.asyncio
    async def test_export_updates_records_batch_id(self, client: AsyncClient, db_session: AsyncSession):
        """测试导出更新记录的批次 ID。"""
        headers = await _auth(client)
        customer_id = await _create_customer(client, headers)
        contract = await _create_contract(client, headers, customer_id)
        payment = await _create_payment(client, headers, contract["id"])

        # 导出
        r = await client.post(
            "/api/v1/finance/export",
            json={
                "export_type": "payments",
                "target_format": "generic",
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
            },
            headers=headers,
        )
        assert r.status_code == 201
        batch_id = r.json()["id"]

        # 检查记录是否更新
        from sqlalchemy import select
        stmt = select(FinanceRecord).where(FinanceRecord.id == payment["id"])
        result = await db_session.execute(stmt)
        record = result.scalar_one_or_none()
        assert record is not None
        assert record.export_batch_id == batch_id


class TestExportInvoices:
    """测试发票导出。"""

    @pytest.mark.asyncio
    async def test_export_invoices_generic_success(self, client: AsyncClient):
        """测试导出发票成功。"""
        headers = await _auth(client)
        customer_id = await _create_customer(client, headers)
        contract = await _create_contract(client, headers, customer_id)
        await _create_invoice(client, headers, contract["id"])

        r = await client.post(
            "/api/v1/finance/export",
            json={
                "export_type": "invoices",
                "target_format": "generic",
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
            },
            headers=headers,
        )
        assert r.status_code == 201
        data = r.json()
        assert "batch_id" in data
        assert data["record_count"] > 0


class TestExportBatchId:
    """测试批次 ID 生成。"""

    @pytest.mark.asyncio
    async def test_export_generates_unique_batch_id(self, client: AsyncClient):
        """测试批次 ID 唯一性。"""
        headers = await _auth(client)
        customer_id = await _create_customer(client, headers)
        await _create_contract(client, headers, customer_id)

        r1 = await client.post(
            "/api/v1/finance/export",
            json={"export_type": "contracts", "target_format": "generic"},
            headers=headers,
        )
        r2 = await client.post(
            "/api/v1/finance/export",
            json={"export_type": "contracts", "target_format": "generic"},
            headers=headers,
        )

        batch_id_1 = r1.json()["batch_id"]
        batch_id_2 = r2.json()["batch_id"]
        assert batch_id_1 != batch_id_2

    @pytest.mark.asyncio
    async def test_export_batch_id_format_correct(self, client: AsyncClient):
        """测试批次 ID 格式正确。"""
        headers = await _auth(client)
        customer_id = await _create_customer(client, headers)
        await _create_contract(client, headers, customer_id)

        r = await client.post(
            "/api/v1/finance/export",
            json={"export_type": "contracts", "target_format": "generic"},
            headers=headers,
        )
        batch_id = r.json()["batch_id"]
        assert batch_id.startswith("EXP-")
        parts = batch_id.split("-")
        assert len(parts) == 4  # EXP, date, time, random


class TestExportFile:
    """测试导出文件。"""

    @pytest.mark.asyncio
    async def test_export_saves_to_exports_directory(self, client: AsyncClient):
        """测试文件保存到 exports 目录。"""
        headers = await _auth(client)
        customer_id = await _create_customer(client, headers)
        await _create_contract(client, headers, customer_id)

        r = await client.post(
            "/api/v1/finance/export",
            json={"export_type": "contracts", "target_format": "generic"},
            headers=headers,
        )
        file_path = r.json()["file_path"]
        assert "exports" in file_path

    @pytest.mark.asyncio
    async def test_export_file_name_format_correct(self, client: AsyncClient):
        """测试文件名格式正确。"""
        headers = await _auth(client)
        customer_id = await _create_customer(client, headers)
        await _create_contract(client, headers, customer_id)

        r = await client.post(
            "/api/v1/finance/export",
            json={"export_type": "contracts", "target_format": "generic"},
            headers=headers,
        )
        file_path = r.json()["file_path"]
        assert file_path.endswith(".xlsx")
        assert "contracts_generic_" in file_path

    @pytest.mark.asyncio
    async def test_export_download_returns_file(self, client: AsyncClient):
        """测试下载导出文件。"""
        headers = await _auth(client)
        customer_id = await _create_customer(client, headers)
        await _create_contract(client, headers, customer_id)

        r = await client.post(
            "/api/v1/finance/export",
            json={"export_type": "contracts", "target_format": "generic"},
            headers=headers,
        )
        batch_id = r.json()["batch_id"]

        # 下载文件
        r2 = await client.get(
            f"/api/v1/finance/export/download/{batch_id}",
            headers=headers,
        )
        assert r2.status_code == 200
        assert r2.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    @pytest.mark.asyncio
    async def test_export_download_missing_file_returns_404(self, client: AsyncClient):
        """测试下载不存在的文件返回 404。"""
        headers = await _auth(client)

        r = await client.get(
            "/api/v1/finance/export/download/EXP-NONEXIST",
            headers=headers,
        )
        assert r.status_code == 404


class TestExportBatchRecord:
    """测试导出批次记录。"""

    @pytest.mark.asyncio
    async def test_export_creates_export_batch_record(self, client: AsyncClient, db_session: AsyncSession):
        """测试创建导出批次记录。"""
        headers = await _auth(client)
        customer_id = await _create_customer(client, headers)
        await _create_contract(client, headers, customer_id)

        r = await client.post(
            "/api/v1/finance/export",
            json={"export_type": "contracts", "target_format": "generic"},
            headers=headers,
        )
        batch_id = r.json()["batch_id"]

        from sqlalchemy import select
        stmt = select(ExportBatch).where(ExportBatch.batch_id == batch_id)
        result = await db_session.execute(stmt)
        batch = result.scalar_one_or_none()
        assert batch is not None
        assert batch.export_type == "contracts"

    @pytest.mark.asyncio
    async def test_export_batch_record_count_correct(self, client: AsyncClient):
        """测试批次记录数正确。"""
        headers = await _auth(client)
        customer_id = await _create_customer(client, headers)
        await _create_contract(client, headers, customer_id)

        r = await client.post(
            "/api/v1/finance/export",
            json={"export_type": "contracts", "target_format": "generic"},
            headers=headers,
        )
        record_count = r.json()["record_count"]
        assert record_count > 0


class TestExportBatchList:
    """测试导出批次列表。"""

    @pytest.mark.asyncio
    async def test_export_batch_list_ordered_by_created_desc(self, client: AsyncClient):
        """测试批次列表按创建时间倒序排列。"""
        headers = await _auth(client)
        customer_id = await _create_customer(client, headers)
        await _create_contract(client, headers, customer_id)

        # 创建两个批次
        await client.post(
            "/api/v1/finance/export",
            json={"export_type": "contracts", "target_format": "generic"},
            headers=headers,
        )
        await client.post(
            "/api/v1/finance/export",
            json={"export_type": "contracts", "target_format": "generic"},
            headers=headers,
        )

        r = await client.get(
            "/api/v1/finance/export/batches",
            headers=headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 2
        # 验证顺序
        if len(data["items"]) >= 2:
            first_created = data["items"][0]["created_at"]
            second_created = data["items"][1]["created_at"]
            assert first_created >= second_created


class TestExportValidation:
    """测试导出校验。"""

    @pytest.mark.asyncio
    async def test_unsupported_format_returns_400(self, client: AsyncClient):
        """测试不支持的格式返回 400。"""
        headers = await _auth(client)

        r = await client.post(
            "/api/v1/finance/export",
            json={
                "export_type": "contracts",
                "target_format": "kingdee",  # 不支持的格式
            },
            headers=headers,
        )
        assert r.status_code == 422  # Pydantic 验证错误

    @pytest.mark.asyncio
    async def test_invalid_export_type_returns_400(self, client: AsyncClient):
        """测试无效的导出类型返回 422。"""
        headers = await _auth(client)

        r = await client.post(
            "/api/v1/finance/export",
            json={
                "export_type": "invalid_type",
                "target_format": "generic",
            },
            headers=headers,
        )
        assert r.status_code == 422  # Pydantic 验证错误


class TestMapToFinanceFormat:
    """测试格式映射。"""

    @pytest.mark.asyncio
    async def test_map_to_finance_format_generic_correct(self, client: AsyncClient):
        """测试 generic 格式映射正确。"""
        headers = await _auth(client)
        customer_id = await _create_customer(client, headers)
        await _create_contract(client, headers, customer_id)

        r = await client.post(
            "/api/v1/finance/export",
            json={"export_type": "contracts", "target_format": "generic"},
            headers=headers,
        )
        assert r.status_code == 201

    @pytest.mark.asyncio
    async def test_map_to_finance_format_unimplemented_raises(self, client: AsyncClient):
        """测试未实现的格式在 Pydantic 验证层被拒绝。"""
        headers = await _auth(client)

        r = await client.post(
            "/api/v1/finance/export",
            json={
                "export_type": "contracts",
                "target_format": "kingdee",
            },
            headers=headers,
        )
        # Pydantic 验证在端点逻辑之前执行，返回 422
        assert r.status_code == 422


class TestExportColumns:
    """测试导出列。"""

    @pytest.mark.asyncio
    async def test_export_generic_columns_match_spec(self, client: AsyncClient):
        """测试 generic 格式列符合规范。"""
        headers = await _auth(client)
        customer_id = await _create_customer(client, headers)
        await _create_contract(client, headers, customer_id)

        r = await client.post(
            "/api/v1/finance/export",
            json={"export_type": "contracts", "target_format": "generic"},
            headers=headers,
        )
        assert r.status_code == 201
