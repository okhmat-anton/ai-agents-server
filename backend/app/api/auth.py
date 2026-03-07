from fastapi import APIRouter, Depends, HTTPException, status, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.database import get_mongodb
from app import database as _db
from app.core.security import (
    hash_password, verify_password, create_access_token, create_refresh_token, decode_token,
)
from app.core.dependencies import get_current_user
from app.mongodb.models.user import MongoUser
from app.mongodb.services import UserService
from app.schemas.auth import (
    LoginRequest, TokenResponse, RefreshRequest, UserResponse, ChangePasswordRequest,
)
from app.schemas.common import MessageResponse
from app.services.log_service import syslog

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request, db: AsyncIOMotorDatabase = Depends(get_mongodb)):
    user_service = UserService(db)
    user = await user_service.get_by_username(body.username)
    
    if not user or not verify_password(body.password, user.password_hash):
        await syslog("warning", f"Failed login attempt for '{body.username}'", source="auth",
                     metadata={"username": body.username, "ip": request.client.host if request.client else None})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        await syslog("warning", f"Login attempt for inactive user '{body.username}'", source="auth")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")

    access_token = create_access_token(str(user.id), user.username)
    refresh_token = create_refresh_token(str(user.id))

    # Store refresh token in Redis
    if _db.redis_client:
        await _db.redis_client.setex(f"refresh:{refresh_token}", 7 * 86400, str(user.id))

    await syslog("info", f"User '{user.username}' logged in", source="auth",
                 metadata={"user_id": str(user.id), "ip": request.client.host if request.client else None})
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: AsyncIOMotorDatabase = Depends(get_mongodb)):
    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    # Check if token is in Redis (not revoked)
    if _db.redis_client:
        stored = await _db.redis_client.get(f"refresh:{body.refresh_token}")
        if not stored:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked")

    user_id = payload["sub"]
    user_service = UserService(db)
    user = await user_service.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    # Revoke old refresh token
    if _db.redis_client:
        await _db.redis_client.delete(f"refresh:{body.refresh_token}")

    access_token = create_access_token(str(user.id), user.username)
    new_refresh = create_refresh_token(str(user.id))

    if _db.redis_client:
        await _db.redis_client.setex(f"refresh:{new_refresh}", 7 * 86400, str(user.id))

    return TokenResponse(access_token=access_token, refresh_token=new_refresh)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    body: RefreshRequest,
    _user: MongoUser = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    if _db.redis_client:
        await _db.redis_client.delete(f"refresh:{body.refresh_token}")
    await syslog("info", f"User '{_user.username}' logged out", source="auth",
                 metadata={"user_id": str(_user.id)})
    return MessageResponse(message="Logged out")


@router.get("/me", response_model=UserResponse)
async def me(user: MongoUser = Depends(get_current_user)):
    return user
