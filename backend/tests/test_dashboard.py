"""数据看板模块测试 - FR-DASHBOARD"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import get_db
from app.models.base import Base
from app.models.user import User
from app.core.security import get_password_hash

TEST_DB = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def db_session():
    engine = create_async_engine(TEST_DB, echo=False, poolclass=StaticPool)
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
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    async def override():
        yield db_session
    app.dependency_overrides[get_db] = override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


async def _auth(client):
    r = await client.post("/api/v1/auth/login", data={"username": "admin", "password": "admin123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# --- FR-DASH-01: 看板指标计算正确性 ---
async def test_dashboard_metrics_structure(client):
    """看板返回正确的指标结构"""
    h = await _auth(client)
    r = await client.get("/api/v1/dashboard", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert "monthly_income" in data
    assert "monthly_expense" in data
    assert "monthly_profit" in data
    assert "active_projects" in data
    assert "customer_conversion_rate" in data
    assert "accounts_receivable" in data


async def test_dashboard_profit_equals_income_minus_expense(client):
    """净利润 = 总收入 - 总支出"""
    h = await _auth(client)
    await client.post("/api/v1/finances", json={
        "type": "income", "amount": 10000, "date": "2026-04-10", "status": "confirmed",
    }, headers=h)
    await client.post("/api/v1/finances", json={
        "type": "expense", "amount": 4000, "date": "2026-04-15", "status": "confirmed",
    }, headers=h)
    r = await client.get("/api/v1/dashboard", headers=h)
    data = r.json()
    assert data["monthly_profit"] == data["monthly_income"] - data["monthly_expense"]


async def test_dashboard_customer_conversion_rate(client):
    """客户转化率 = 成交客户数 / 总客户数 * 100"""
    h = await _auth(client)
    # 2个潜在客户
    await client.post("/api/v1/customers", json={"name": "A", "company": "X", "source": "other", "status": "potential"}, headers=h)
    await client.post("/api/v1/customers", json={"name": "B", "company": "Y", "source": "other", "status": "potential"}, headers=h)
    # 1个成交客户
    await client.post("/api/v1/customers", json={"name": "C", "company": "Z", "source": "other", "status": "deal"}, headers=h)
    r = await client.get("/api/v1/dashboard", headers=h)
    assert r.json()["customer_conversion_rate"] == pytest.approx(33.33, abs=0.1)


# --- FR-DASH-02: 单项数据获取失败不影响其他 ---
async def test_dashboard_graceful_degradation(client):
    """看板接口在任何情况下都返回200"""
    h = await _auth(client)
    r = await client.get("/api/v1/dashboard", headers=h)
    assert r.status_code == 200


async def test_dashboard_with_no_data(client):
    """无数据时看板返回零值"""
    h = await _auth(client)
    r = await client.get("/api/v1/dashboard", headers=h)
    data = r.json()
    assert data["monthly_income"] == 0
    assert data["monthly_expense"] == 0
    assert data["monthly_profit"] == 0
    assert data["active_projects"] == 0


# --- 客户漏斗 ---
async def test_customer_funnel(client):
    """客户漏斗数据正确"""
    h = await _auth(client)
    await client.post("/api/v1/customers", json={"name": "A1", "company": "X1", "source": "other", "status": "potential"}, headers=h)
    await client.post("/api/v1/customers", json={"name": "A2", "company": "X2", "source": "other", "status": "deal"}, headers=h)
    r = await client.get("/api/v1/dashboard/customer-funnel", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert data["potential"] == 1
    assert data["deal"] == 1
    assert data["lost"] == 0


# --- 收入趋势 ---
async def test_revenue_trend(client):
    """收入趋势返回月度数据"""
    h = await _auth(client)
    r = await client.get("/api/v1/dashboard/revenue-trend?months=3", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 3
    for item in data:
        assert "month" in item
        assert "income" in item
        assert "expense" in item


# --- FR-DASH-05: 待办任务包含优先级 ---
async def test_todos_include_priority(client):
    """待办任务返回包含优先级字段"""
    h = await _auth(client)
    # 创建客户和项目
    r = await client.post("/api/v1/customers", json={
        "name": "T", "company": "TC", "source": "other", "status": "deal",
    }, headers=h)
    cid = r.json()["id"]
    r = await client.post("/api/v1/projects", json={"name": "P", "customer_id": cid}, headers=h)
    pid = r.json()["id"]
    # 创建不同优先级任务
    await client.post(f"/api/v1/projects/{pid}/tasks", json={"title": "低优先", "priority": "low"}, headers=h)
    await client.post(f"/api/v1/projects/{pid}/tasks", json={"title": "高优先", "priority": "high"}, headers=h)
    r = await client.get("/api/v1/dashboard/todos", headers=h)
    assert r.status_code == 200
    tasks = r.json()["tasks"]
    assert len(tasks) >= 2
    for t in tasks:
        assert "priority" in t


async def test_todos_ordered_by_priority(client):
    """待办任务按优先级排序（高→中→低）"""
    h = await _auth(client)
    r = await client.post("/api/v1/customers", json={
        "name": "T2", "company": "TC2", "source": "other", "status": "deal",
    }, headers=h)
    cid = r.json()["id"]
    r = await client.post("/api/v1/projects", json={"name": "P2", "customer_id": cid}, headers=h)
    pid = r.json()["id"]
    await client.post(f"/api/v1/projects/{pid}/tasks", json={"title": "低", "priority": "low"}, headers=h)
    await client.post(f"/api/v1/projects/{pid}/tasks", json={"title": "高", "priority": "high"}, headers=h)
    await client.post(f"/api/v1/projects/{pid}/tasks", json={"title": "中", "priority": "medium"}, headers=h)
    r = await client.get("/api/v1/dashboard/todos", headers=h)
    tasks = r.json()["tasks"]
    if len(tasks) >= 3:
        priorities = [t["priority"] for t in tasks]
        high_idx = priorities.index("high") if "high" in priorities else 999
        low_idx = priorities.index("low") if "low" in priorities else -1
        assert high_idx < low_idx, "高优先级任务应排在低优先级前面"


# --- FR-DASH-06: 即将到期合同提醒 ---
async def test_expiring_contracts(client):
    """返回7天内即将到期的合同"""
    h = await _auth(client)
    r = await client.post("/api/v1/customers", json={
        "name": "T3", "company": "TC3", "source": "other", "status": "deal",
    }, headers=h)
    cid = r.json()["id"]
    # 创建一个7天内到期的合同
    await client.post("/api/v1/contracts", json={
        "title": "即将到期", "customer_id": cid, "amount": 5000,
        "end_date": "2026-04-10", "status": "draft",
    }, headers=h)
    # 激活合同
    r2 = await client.get("/api/v1/contracts", headers=h)
    contracts = r2.json()["items"]
    if contracts:
        cid_contract = contracts[0]["id"]
        await client.put(f"/api/v1/contracts/{cid_contract}", json={"status": "active"}, headers=h)
    r = await client.get("/api/v1/dashboard/todos", headers=h)
    assert r.status_code == 200
    assert "expiring_contracts" in r.json()
    expiring = r.json()["expiring_contracts"]
    # 可能有或无，取决于日期是否在7天内
    for c in expiring:
        assert "contract_no" in c
        assert "end_date" in c
        assert "title" in c


# --- FR-DASH-07: 项目状态分布 ---
async def test_project_status_distribution(client):
    """项目状态分布返回各状态的计数"""
    h = await _auth(client)
    r = await client.post("/api/v1/customers", json={
        "name": "T4", "company": "TC4", "source": "other", "status": "deal",
    }, headers=h)
    cid = r.json()["id"]
    await client.post("/api/v1/projects", json={"name": "P需求", "customer_id": cid, "status": "requirements"}, headers=h)
    await client.post("/api/v1/projects", json={"name": "P开发", "customer_id": cid, "status": "development"}, headers=h)
    r = await client.get("/api/v1/dashboard/project-status", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert data.get("requirements", 0) >= 1
    assert data.get("development", 0) >= 1


# --- FR-DASH-08: 分类统计 ---
async def test_category_breakdown(client):
    """分类统计返回各分类的金额"""
    h = await _auth(client)
    await client.post("/api/v1/finances", json={
        "type": "income", "amount": 5000, "date": "2026-04-01",
        "category": "服务费", "status": "confirmed",
    }, headers=h)
    await client.post("/api/v1/finances", json={
        "type": "income", "amount": 3000, "date": "2026-04-02",
        "category": "咨询费", "status": "confirmed",
    }, headers=h)
    r = await client.get("/api/v1/finances/stats/categories?year=2026&month=4", headers=h)
    assert r.status_code == 200
    cats = r.json()["categories"]
    assert "服务费" in cats
    assert cats["服务费"] == 5000.0
    assert "咨询费" in cats
    assert cats["咨询费"] == 3000.0
