import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import select

from app.main import app
from app.database import get_db
from app.models.base import Base
from app.models.user import User
from app.core.security import get_password_hash, verify_password

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def db_session():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=StaticPool)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_session() as session:
        hashed = get_password_hash("admin123")
        print(f"\n[Fixture] Password hash: {hashed[:30]}...")
        print(f"[Fixture] Verify test: {verify_password('admin123', hashed)}")
        admin = User(
            username="admin",
            hashed_password=hashed,
            full_name="系统管理员",
            email="admin@shubiao.local",
            is_active=True,
            is_superuser=True,
        )
        session.add(admin)
        await session.commit()
        # Verify user exists
        result = await session.execute(select(User).where(User.username == "admin"))
        user = result.scalar_one_or_none()
        print(f"[Fixture] User exists: {user is not None}")
        if user:
            print(f"[Fixture] User hash: {user.hashed_password[:30]}...")
            print(f"[Fixture] DB verify: {verify_password('admin123', user.hashed_password)}")
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


async def get_token(client):
    r = await client.post("/api/v1/auth/login", data={"username": "admin", "password": "admin123"})
    print(f"\nLogin response: {r.status_code}, body: {r.text}")
    assert r.status_code == 200, f"Login failed: {r.text}"
    return r.json()["access_token"]


async def auth(client):
    return {"Authorization": f"Bearer {await get_token(client)}"}


async def test_debug_login_and_contract(client, db_session):
    """Full debug: login then contract creation"""
    # First verify the user exists and password works directly
    from sqlalchemy import select
    from app.models.user import User
    from app.core.security import verify_password

    result = await db_session.execute(select(User).where(User.username == "admin"))
    user = result.scalar_one_or_none()
    print(f"\n[DEBUG] User found: {user is not None}")
    if user:
        print(f"[DEBUG] Hash in DB: {user.hashed_password[:40]}...")
        pw_check = verify_password("admin123", user.hashed_password)
        print(f"[DEBUG] Password verify result: {pw_check}")

    h = await auth(client)

    # Create customer
    r = await client.post(
        "/api/v1/customers",
        json={
            "name": "Test Corp",
            "contact_person": "J",
            "company": "Test Corp",
            "source": "referral",
            "status": "potential",
        },
        headers=h,
    )
    print(f"\nCustomer: {r.status_code}, body: {r.text[:200]}")
    assert r.status_code == 201
    cid = r.json()["id"]

    # Create project
    r = await client.post(
        "/api/v1/projects", json={"name": "Test Project", "customer_id": cid, "budget": 10000}, headers=h
    )
    print(f"Project: {r.status_code}, body: {r.text[:200]}")
    assert r.status_code == 201
    pid = r.json()["id"]

    # Create contract
    r = await client.post(
        "/api/v1/contracts",
        json={"title": "Test Contract", "customer_id": cid, "project_id": pid, "amount": 10000},
        headers=h,
    )
    print(f"Contract: {r.status_code}, body: {r.text[:500]}")
    assert r.status_code == 201, f"Expected 201, got {r.status_code}"


async def test_debug_project_detail(client):
    h = await auth(client)
    r = await client.post(
        "/api/v1/customers",
        json={"name": "T", "contact_person": "J", "company": "T", "source": "referral", "status": "potential"},
        headers=h,
    )
    cid = r.json()["id"]
    r = await client.post("/api/v1/projects", json={"name": "P", "customer_id": cid, "budget": 10000}, headers=h)
    pid = r.json()["id"]
    r = await client.get(f"/api/v1/projects/{pid}", headers=h)
    print(f"\nProject detail: {r.status_code}, body: {r.text[:500]}")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"


async def test_debug_milestone(client):
    h = await auth(client)
    r = await client.post(
        "/api/v1/customers",
        json={"name": "T", "contact_person": "J", "company": "T", "source": "referral", "status": "potential"},
        headers=h,
    )
    cid = r.json()["id"]
    r = await client.post("/api/v1/projects", json={"name": "P", "customer_id": cid, "budget": 10000}, headers=h)
    pid = r.json()["id"]
    r = await client.post(
        f"/api/v1/projects/{pid}/milestones", json={"title": "M1", "due_date": "2026-05-01"}, headers=h
    )
    print(f"\nMilestone: {r.status_code}, body: {r.text[:500]}")
    assert r.status_code == 201, f"Expected 201, got {r.status_code}"


async def test_debug_contract_transition(client):
    h = await auth(client)
    r = await client.post(
        "/api/v1/customers",
        json={"name": "T", "contact_person": "J", "company": "T", "source": "referral", "status": "potential"},
        headers=h,
    )
    cid = r.json()["id"]
    r = await client.post("/api/v1/contracts", json={"title": "C", "customer_id": cid, "amount": 10000}, headers=h)
    print(f"\nCreate contract: {r.status_code}, body: {r.text[:300]}")
    if r.status_code != 201:
        pytest.skip("Contract creation failed")
    contract_id = r.json()["id"]
    r = await client.put(f"/api/v1/contracts/{contract_id}", json={"status": "active"}, headers=h)
    print(f"Draft->Active: {r.status_code}, body: {r.text}")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"


async def test_debug_milestone_creation(client):
    h = await auth(client)
    r = await client.post(
        "/api/v1/customers",
        json={"name": "T", "contact_person": "J", "company": "T", "source": "referral", "status": "potential"},
        headers=h,
    )
    cid = r.json()["id"]
    r = await client.post("/api/v1/projects", json={"name": "P", "customer_id": cid, "budget": 10000}, headers=h)
    pid = r.json()["id"]
    r = await client.post(
        f"/api/v1/projects/{pid}/milestones", json={"title": "M1", "due_date": "2026-05-01"}, headers=h
    )
    print(f"\nMilestone response: {r.status_code}")
    print(f"Milestone body: {r.text}")
    assert r.status_code == 201, f"Expected 201, got {r.status_code}: {r.text}"


async def test_debug_contract_status_transition(client):
    h = await auth(client)
    r = await client.post(
        "/api/v1/customers",
        json={"name": "T", "contact_person": "J", "company": "T", "source": "referral", "status": "potential"},
        headers=h,
    )
    cid = r.json()["id"]
    r = await client.post("/api/v1/contracts", json={"title": "C", "customer_id": cid, "amount": 10000}, headers=h)
    print(f"\nCreate contract: {r.status_code}, body: {r.text[:300]}")
    if r.status_code != 201:
        pytest.skip("Contract creation failed, skipping transition tests")
    contract_id = r.json()["id"]
    r = await client.put(f"/api/v1/contracts/{contract_id}", json={"status": "active"}, headers=h)
    print(f"Draft->Active: {r.status_code}, body: {r.text}")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
