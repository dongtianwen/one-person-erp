"""v1.8 发票台账管理测试。"""

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
from app.models.invoice import Invoice  # 必须导入以创建表
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
        },
        headers=headers,
    )
    return r.json()


class TestInvoiceCreation:
    """测试发票创建。"""

    async def test_create_invoice_success(self, client: AsyncClient):
        """测试成功创建发票。"""
        h = await _auth(client)
        cid = await _create_customer(client, h)
        contract = await _create_contract(client, h, cid)

        response = await client.post(
            "/api/v1/invoices",
            json={
                "contract_id": contract["id"],
                "invoice_type": "standard",
                "invoice_date": "2026-04-09",
                "amount_excluding_tax": 10000.00,
                "tax_rate": 0.13,
            },
            headers=h,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["invoice_no"].startswith("INV-20260409-")
        assert data["status"] == "draft"
        assert data["tax_amount"] == "1300.00"
        assert data["total_amount"] == "11300.00"

    async def test_create_invoice_invalid_contract(self, client: AsyncClient):
        """测试关联合同不存在。"""
        h = await _auth(client)
        response = await client.post(
            "/api/v1/invoices",
            json={
                "contract_id": 99999,
                "invoice_type": "standard",
                "invoice_date": "2026-04-09",
                "amount_excluding_tax": 10000.00,
            },
            headers=h,
        )
        assert response.status_code == 422
        assert "发票必须关联合同" in response.json()["detail"]

    async def test_create_invoice_negative_amount(self, client: AsyncClient):
        """测试金额为负数。"""
        h = await _auth(client)
        cid = await _create_customer(client, h)
        contract = await _create_contract(client, h, cid)

        response = await client.post(
            "/api/v1/invoices",
            json={
                "contract_id": contract["id"],
                "invoice_type": "standard",
                "invoice_date": "2026-04-09",
                "amount_excluding_tax": -100.00,
            },
            headers=h,
        )
        assert response.status_code == 422

    async def test_create_invoice_exceeds_contract(self, client: AsyncClient):
        """测试累计金额超限。"""
        h = await _auth(client)
        cid = await _create_customer(client, h)
        # 合同金额 50000
        contract = await _create_contract(client, h, cid, Decimal("50000.00"))

        # 先创建一张 40000 不含税 = 45200 含税的发票
        await client.post(
            "/api/v1/invoices",
            json={
                "contract_id": contract["id"],
                "invoice_type": "standard",
                "invoice_date": "2026-04-09",
                "amount_excluding_tax": 40000.00,
            },
            headers=h,
        )

        # 再创建一张 5000 不含税 = 5650 含税的发票，总计 50850 > 50000
        response = await client.post(
            "/api/v1/invoices",
            json={
                "contract_id": contract["id"],
                "invoice_type": "standard",
                "invoice_date": "2026-04-09",
                "amount_excluding_tax": 5000.00,
            },
            headers=h,
        )
        assert response.status_code == 422
        assert "开票金额已超合同金额" in response.json()["detail"]


class TestInvoiceListing:
    """测试发票列表。"""

    async def test_list_invoices_ordered(self, client: AsyncClient):
        """测试列表按日期倒序排列。"""
        h = await _auth(client)
        cid = await _create_customer(client, h)
        contract = await _create_contract(client, h, cid)

        # 创建三张不同日期的发票
        for i in range(3):
            await client.post(
                "/api/v1/invoices",
                json={
                    "contract_id": contract["id"],
                    "invoice_type": "standard",
                    "invoice_date": f"2026-04-0{i+1}",
                    "amount_excluding_tax": 1000.00,
                },
                headers=h,
            )

        response = await client.get("/api/v1/invoices", headers=h)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        # 验证倒序（最新在前）
        dates = [item["invoice_date"] for item in data["items"]]
        assert dates == sorted(dates, reverse=True)

    async def test_filter_invoices_by_status(self, client: AsyncClient):
        """测试按状态筛选。"""
        h = await _auth(client)
        cid = await _create_customer(client, h)
        contract = await _create_contract(client, h, cid)

        # 创建草稿发票
        await client.post(
            "/api/v1/invoices",
            json={
                "contract_id": contract["id"],
                "invoice_type": "standard",
                "invoice_date": "2026-04-09",
                "amount_excluding_tax": 1000.00,
            },
            headers=h,
        )

        response = await client.get("/api/v1/invoices?status=draft", headers=h)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["status"] == "draft"

    async def test_filter_invoices_by_contract(self, client: AsyncClient):
        """测试按合同筛选。"""
        h = await _auth(client)
        cid = await _create_customer(client, h)
        contract = await _create_contract(client, h, cid)

        await client.post(
            "/api/v1/invoices",
            json={
                "contract_id": contract["id"],
                "invoice_type": "standard",
                "invoice_date": "2026-04-09",
                "amount_excluding_tax": 1000.00,
            },
            headers=h,
        )

        response = await client.get(f'/api/v1/invoices?contract_id={contract["id"]}', headers=h)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1


class TestInvoiceStatusTransitions:
    """测试发票状态流转。"""

    async def _create_draft_invoice(self, client: AsyncClient, headers: dict) -> dict:
        """辅助函数：创建草稿发票。"""
        cid = await _create_customer(client, headers)
        contract = await _create_contract(client, headers, cid)
        response = await client.post(
            "/api/v1/invoices",
            json={
                "contract_id": contract["id"],
                "invoice_type": "standard",
                "invoice_date": "2026-04-09",
                "amount_excluding_tax": 1000.00,
            },
            headers=headers,
        )
        return response.json()

    async def test_draft_to_issued(self, client: AsyncClient):
        """测试 draft → issued。"""
        h = await _auth(client)
        invoice = await self._create_draft_invoice(client, h)

        response = await client.post(f'/api/v1/invoices/{invoice["id"]}/issue', headers=h)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "issued"
        assert data["issued_at"] is not None

    async def test_issued_to_received(self, client: AsyncClient):
        """测试 issued → received。"""
        h = await _auth(client)
        invoice = await self._create_draft_invoice(client, h)

        await client.post(f'/api/v1/invoices/{invoice["id"]}/issue', headers=h)
        response = await client.post(
            f'/api/v1/invoices/{invoice["id"]}/receive',
            json={"received_by": "财务部"},
            headers=h,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "received"
        assert data["received_at"] is not None
        assert data["received_by"] == "财务部"

    async def test_received_to_verified(self, client: AsyncClient):
        """测试 received → verified。"""
        h = await _auth(client)
        invoice = await self._create_draft_invoice(client, h)

        await client.post(f'/api/v1/invoices/{invoice["id"]}/issue', headers=h)
        await client.post(f'/api/v1/invoices/{invoice["id"]}/receive', headers=h)
        response = await client.post(f'/api/v1/invoices/{invoice["id"]}/verify', headers=h)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "verified"
        assert data["verified_at"] is not None

    async def test_invalid_transition(self, client: AsyncClient):
        """测试非法状态流转。"""
        h = await _auth(client)
        invoice = await self._create_draft_invoice(client, h)

        # 先核销发票
        await client.post(f'/api/v1/invoices/{invoice["id"]}/issue', headers=h)
        await client.post(f'/api/v1/invoices/{invoice["id"]}/receive', headers=h)
        await client.post(f'/api/v1/invoices/{invoice["id"]}/verify', headers=h)

        # verified 不能再流转回 issued
        response = await client.post(f'/api/v1/invoices/{invoice["id"]}/issue', headers=h)
        assert response.status_code == 409

    async def test_verified_cannot_change(self, client: AsyncClient):
        """测试已核销发票不可变更。"""
        h = await _auth(client)
        invoice = await self._create_draft_invoice(client, h)

        await client.post(f'/api/v1/invoices/{invoice["id"]}/issue', headers=h)
        await client.post(f'/api/v1/invoices/{invoice["id"]}/receive', headers=h)
        await client.post(f'/api/v1/invoices/{invoice["id"]}/verify', headers=h)

        response = await client.post(f'/api/v1/invoices/{invoice["id"]}/issue', headers=h)
        assert response.status_code == 409
        assert "发票已核销" in response.json()["detail"]

    async def test_cancel_draft(self, client: AsyncClient):
        """测试作废草稿发票。"""
        h = await _auth(client)
        invoice = await self._create_draft_invoice(client, h)

        response = await client.post(f'/api/v1/invoices/{invoice["id"]}/cancel', headers=h)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"

    async def test_cancelled_cannot_verify(self, client: AsyncClient):
        """测试已作废发票不可核销。"""
        h = await _auth(client)
        invoice = await self._create_draft_invoice(client, h)

        await client.post(f'/api/v1/invoices/{invoice["id"]}/cancel', headers=h)
        response = await client.post(f'/api/v1/invoices/{invoice["id"]}/verify', headers=h)
        assert response.status_code == 409
        assert "已作废" in response.json()["detail"]


class TestInvoiceUpdate:
    """测试发票更新。"""

    async def _create_draft_invoice(self, client: AsyncClient, headers: dict) -> dict:
        """辅助函数：创建草稿发票。"""
        cid = await _create_customer(client, headers)
        contract = await _create_contract(client, headers, cid)
        response = await client.post(
            "/api/v1/invoices",
            json={
                "contract_id": contract["id"],
                "invoice_type": "standard",
                "invoice_date": "2026-04-09",
                "amount_excluding_tax": 1000.00,
            },
            headers=headers,
        )
        return response.json()

    async def test_update_draft_all_fields(self, client: AsyncClient):
        """测试更新草稿发票所有字段。"""
        h = await _auth(client)
        invoice = await self._create_draft_invoice(client, h)

        response = await client.patch(
            f'/api/v1/invoices/{invoice["id"]}',
            json={
                "amount_excluding_tax": 2000.00,
                "notes": "更新备注",
            },
            headers=h,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["amount_excluding_tax"] == "2000.00"
        assert data["notes"] == "更新备注"
        # 验证税额重新计算
        assert data["tax_amount"] == "260.00"
        assert data["total_amount"] == "2260.00"

    async def test_update_issued_only_notes(self, client: AsyncClient):
        """测试已开具发票只能修改备注。"""
        h = await _auth(client)
        invoice = await self._create_draft_invoice(client, h)

        await client.post(f'/api/v1/invoices/{invoice["id"]}/issue', headers=h)

        response = await client.patch(
            f'/api/v1/invoices/{invoice["id"]}',
            json={
                "amount_excluding_tax": 2000.00,
                "notes": "新备注",
            },
            headers=h,
        )
        assert response.status_code == 409
        assert "只能修改备注" in response.json()["detail"]

    async def test_update_verified_rejected(self, client: AsyncClient):
        """测试已核销发票不可修改。"""
        h = await _auth(client)
        invoice = await self._create_draft_invoice(client, h)

        await client.post(f'/api/v1/invoices/{invoice["id"]}/issue', headers=h)
        await client.post(f'/api/v1/invoices/{invoice["id"]}/receive', headers=h)
        await client.post(f'/api/v1/invoices/{invoice["id"]}/verify', headers=h)

        response = await client.patch(
            f'/api/v1/invoices/{invoice["id"]}',
            json={"notes": "尝试修改"},
            headers=h,
        )
        assert response.status_code == 409
        assert "已核销发票不可修改" in response.json()["detail"]


class TestInvoiceDeletion:
    """测试发票删除。"""

    async def _create_draft_invoice(self, client: AsyncClient, headers: dict) -> dict:
        """辅助函数：创建草稿发票。"""
        cid = await _create_customer(client, headers)
        contract = await _create_contract(client, headers, cid)
        response = await client.post(
            "/api/v1/invoices",
            json={
                "contract_id": contract["id"],
                "invoice_type": "standard",
                "invoice_date": "2026-04-09",
                "amount_excluding_tax": 1000.00,
            },
            headers=headers,
        )
        return response.json()

    async def test_delete_draft_success(self, client: AsyncClient):
        """测试删除草稿发票。"""
        h = await _auth(client)
        invoice = await self._create_draft_invoice(client, h)

        response = await client.delete(f'/api/v1/invoices/{invoice["id"]}', headers=h)
        assert response.status_code == 204

    async def test_delete_issued_rejected(self, client: AsyncClient):
        """测试删除已开具发票失败。"""
        h = await _auth(client)
        invoice = await self._create_draft_invoice(client, h)

        await client.post(f'/api/v1/invoices/{invoice["id"]}/issue', headers=h)

        response = await client.delete(f'/api/v1/invoices/{invoice["id"]}', headers=h)
        assert response.status_code == 409
        assert "已开具发票不可删除" in response.json()["detail"]

    async def test_delete_verified_rejected(self, client: AsyncClient):
        """测试删除已核销发票失败。"""
        h = await _auth(client)
        invoice = await self._create_draft_invoice(client, h)

        await client.post(f'/api/v1/invoices/{invoice["id"]}/issue', headers=h)
        await client.post(f'/api/v1/invoices/{invoice["id"]}/receive', headers=h)
        await client.post(f'/api/v1/invoices/{invoice["id"]}/verify', headers=h)

        response = await client.delete(f'/api/v1/invoices/{invoice["id"]}', headers=h)
        assert response.status_code == 409
        assert "已核销发票不可删除" in response.json()["detail"]


class TestInvoiceSummary:
    """测试发票汇总统计。"""

    async def test_get_summary(self, client: AsyncClient):
        """测试获取汇总统计。"""
        h = await _auth(client)
        cid = await _create_customer(client, h)
        contract = await _create_contract(client, h, cid)

        # 创建不同状态的发票
        r1 = await client.post(
            "/api/v1/invoices",
            json={
                "contract_id": contract["id"],
                "invoice_type": "standard",
                "invoice_date": "2026-04-09",
                "amount_excluding_tax": 1000.00,
            },
            headers=h,
        )
        inv1 = r1.json()

        await client.post(f'/api/v1/invoices/{inv1["id"]}/issue', headers=h)

        # 再创建一张 draft 状态的发票
        await client.post(
            "/api/v1/invoices",
            json={
                "contract_id": contract["id"],
                "invoice_type": "standard",
                "invoice_date": "2026-04-09",
                "amount_excluding_tax": 2000.00,
            },
            headers=h,
        )

        response = await client.get("/api/v1/invoices/summary", headers=h)
        assert response.status_code == 200
        data = response.json()
        # 验证汇总返回了所有状态
        assert "draft" in data
        assert "issued" in data
        assert "received" in data
        assert "verified" in data
        assert "cancelled" in data
        # 验证有发票被创建
        assert data["draft"]["count"] + data["issued"]["count"] >= 1


class TestInvoiceTypes:
    """测试发票类型。"""

    async def test_create_with_valid_type(self, client: AsyncClient):
        """测试有效发票类型。"""
        h = await _auth(client)
        cid = await _create_customer(client, h)
        contract = await _create_contract(client, h, cid)

        for inv_type in ["standard", "ordinary", "electronic", "small_scale"]:
            response = await client.post(
                "/api/v1/invoices",
                json={
                    "contract_id": contract["id"],
                    "invoice_type": inv_type,
                    "invoice_date": "2026-04-09",
                    "amount_excluding_tax": 1000.00,
                },
                headers=h,
            )
            assert response.status_code == 201

    async def test_default_type_is_standard(self, client: AsyncClient):
        """测试默认类型为 standard。"""
        h = await _auth(client)
        cid = await _create_customer(client, h)
        contract = await _create_contract(client, h, cid)

        response = await client.post(
            "/api/v1/invoices",
            json={
                "contract_id": contract["id"],
                "invoice_date": "2026-04-09",
                "amount_excluding_tax": 1000.00,
            },
            headers=h,
        )
        assert response.status_code == 201
        assert response.json()["invoice_type"] == "standard"

    async def test_invalid_type_rejected(self, client: AsyncClient):
        """测试无效类型拒绝。"""
        h = await _auth(client)
        cid = await _create_customer(client, h)
        contract = await _create_contract(client, h, cid)

        response = await client.post(
            "/api/v1/invoices",
            json={
                "contract_id": contract["id"],
                "invoice_type": "invalid_type",
                "invoice_date": "2026-04-09",
                "amount_excluding_tax": 1000.00,
            },
            headers=h,
        )
        assert response.status_code == 422


class TestContractInvoices:
    """测试合同关联发票列表。"""

    async def test_get_contract_invoices(self, client: AsyncClient):
        """测试获取合同关联发票。"""
        h = await _auth(client)
        cid = await _create_customer(client, h)
        contract = await _create_contract(client, h, cid)

        # 创建两张发票
        await client.post(
            "/api/v1/invoices",
            json={
                "contract_id": contract["id"],
                "invoice_type": "standard",
                "invoice_date": "2026-04-09",
                "amount_excluding_tax": 1000.00,
            },
            headers=h,
        )
        await client.post(
            "/api/v1/invoices",
            json={
                "contract_id": contract["id"],
                "invoice_type": "standard",
                "invoice_date": "2026-04-10",
                "amount_excluding_tax": 2000.00,
            },
            headers=h,
        )

        response = await client.get(f'/api/v1/contracts/{contract["id"]}/invoices', headers=h)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2
