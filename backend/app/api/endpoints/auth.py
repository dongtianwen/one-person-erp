from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.core.exceptions import InvalidCredentialsException, AccountLockedException
from app.api.deps import get_current_user

router = APIRouter()


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: int
    username: str
    full_name: str | None
    email: str | None

    class Config:
        from_attributes = True


@router.post("/login", response_model=TokenResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == form_data.username))
    user = result.scalar_one_or_none()

    if user is None:
        raise InvalidCredentialsException()

    if user.locked_until:
        locked_until = datetime.fromisoformat(user.locked_until)
        if datetime.utcnow() < locked_until:
            raise AccountLockedException()
        else:
            user.login_attempts = 0
            user.locked_until = None
            await db.commit()

    if not verify_password(form_data.password, user.hashed_password):
        user.login_attempts = (user.login_attempts or 0) + 1
        if user.login_attempts >= 5:
            user.locked_until = (datetime.utcnow() + timedelta(minutes=30)).isoformat()
            await db.commit()
            raise AccountLockedException()
        await db.commit()
        raise InvalidCredentialsException()

    user.login_attempts = 0
    user.locked_until = None
    await db.commit()

    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return TokenResponse(access_token=access_token, refresh_token=refresh_token, token_type="bearer")


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_token(request.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="无效的刷新令牌")

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="用户不存在或已停用")

    access_token = create_access_token(data={"sub": str(user.id)})
    new_refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return TokenResponse(access_token=access_token, refresh_token=new_refresh_token, token_type="bearer")


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse(
        id=current_user.id, username=current_user.username, full_name=current_user.full_name, email=current_user.email
    )


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    return {"message": "登出成功"}


async def create_default_admin(db: AsyncSession):
    result = await db.execute(select(User))
    users = result.scalars().all()
    if not users:
        admin = User(
            username="admin",
            hashed_password=get_password_hash("admin123"),
            full_name="系统管理员",
            email="admin@shubiao.local",
            is_active=True,
            is_superuser=True,
        )
        db.add(admin)
        await db.commit()
