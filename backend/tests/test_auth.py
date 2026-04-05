"""认证模块测试 - FR-AUTH"""
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
from app.core.security import get_password_hash, create_access_token, create_refresh_token, decode_token

TEST_DB = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def db_session():
    engine = create_async_engine(TEST_DB, echo=False, poolclass=StaticPool)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
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


async def _create_user(db_session, username="testuser", password="pass123"):
    user = User(
        username=username,
        hashed_password=get_password_hash(password),
        full_name="测试用户",
        email=f"{username}@test.com",
        is_active=True,
        is_superuser=False,
        login_attempts=0,
    )
    db_session.add(user)
    await db_session.commit()
    return user


# --- FR-AUTH-01: 密码错误5次后账户锁定30分钟 ---
async def test_login_success(client, db_session):
    """正常登录成功"""
    await _create_user(db_session)
    r = await client.post("/api/v1/auth/login", data={"username": "testuser", "password": "pass123"})
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


async def test_login_wrong_password_increments_attempts(client, db_session):
    """密码错误递增登录尝试次数"""
    await _create_user(db_session)
    r = await client.post("/api/v1/auth/login", data={"username": "testuser", "password": "wrong"})
    assert r.status_code == 401
    result = await db_session.execute(select(User).where(User.username == "testuser"))
    user = result.scalar_one()
    assert user.login_attempts == 1


async def test_account_locked_after_5_failures(client, db_session):
    """连续5次密码错误后账户锁定"""
    await _create_user(db_session)
    for i in range(4):
        r = await client.post("/api/v1/auth/login", data={"username": "testuser", "password": "wrong"})
        assert r.status_code == 401
    # 第5次应触发锁定
    r = await client.post("/api/v1/auth/login", data={"username": "testuser", "password": "wrong"})
    assert r.status_code == 423
    # 再次尝试（即使密码正确）也应被锁定
    r = await client.post("/api/v1/auth/login", data={"username": "testuser", "password": "pass123"})
    assert r.status_code == 423


async def test_locked_user_has_locked_until(client, db_session):
    """锁定后 locked_until 字段非空"""
    await _create_user(db_session)
    for _ in range(5):
        await client.post("/api/v1/auth/login", data={"username": "testuser", "password": "wrong"})
    result = await db_session.execute(select(User).where(User.username == "testuser"))
    user = result.scalar_one()
    assert user.locked_until is not None


# --- FR-AUTH-02: Access Token 有效期 30 分钟, Refresh Token 7 天 ---
async def test_access_token_contains_type(client, db_session):
    """Access token 包含 type=access"""
    await _create_user(db_session)
    r = await client.post("/api/v1/auth/login", data={"username": "testuser", "password": "pass123"})
    token = r.json()["access_token"]
    payload = decode_token(token)
    assert payload is not None
    assert payload.get("type") == "access"


async def test_refresh_token_contains_type(client, db_session):
    """Refresh token 包含 type=refresh"""
    await _create_user(db_session)
    r = await client.post("/api/v1/auth/login", data={"username": "testuser", "password": "pass123"})
    token = r.json()["refresh_token"]
    payload = decode_token(token)
    assert payload is not None
    assert payload.get("type") == "refresh"


async def test_refresh_token_works(client, db_session):
    """Refresh token 可以获取新 token"""
    await _create_user(db_session)
    r = await client.post("/api/v1/auth/login", data={"username": "testuser", "password": "pass123"})
    refresh = r.json()["refresh_token"]
    r2 = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert r2.status_code == 200
    assert "access_token" in r2.json()


# --- FR-AUTH-03: 登出后 Token 失效 ---
async def test_invalid_token_rejected(client):
    """无效 token 无法访问受保护接口"""
    r = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
    assert r.status_code == 401


async def test_no_token_rejected(client):
    """无 token 无法访问受保护接口"""
    r = await client.get("/api/v1/auth/me")
    assert r.status_code == 401


async def test_me_returns_user_info(client, db_session):
    """有效 token 返回用户信息"""
    await _create_user(db_session)
    r = await client.post("/api/v1/auth/login", data={"username": "testuser", "password": "pass123"})
    token = r.json()["access_token"]
    r2 = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 200
    assert r2.json()["username"] == "testuser"
