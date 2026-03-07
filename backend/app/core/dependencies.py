import uuid
from fastapi import Depends, HTTPException, status, Header, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.database import get_mongodb
from app.core.security import decode_token, verify_api_key
from app.mongodb.models.user import MongoUser
from app.mongodb.models.api_key import MongoApiKey
from app.mongodb.services import UserService, ApiKeyService
from datetime import datetime, timezone

security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
) -> MongoUser:
    # Try API Key first
    if x_api_key:
        return await _authenticate_api_key(x_api_key, db)

    # Try JWT
    if credentials:
        return await _authenticate_jwt(credentials.credentials, db)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_ws_user(
    token: str | None = Query(None),
    api_key: str | None = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
) -> MongoUser:
    """Authenticate WebSocket connections via query params."""
    if api_key:
        return await _authenticate_api_key(api_key, db)
    if token:
        return await _authenticate_jwt(token, db)
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


async def _authenticate_jwt(token: str, db: AsyncIOMotorDatabase) -> MongoUser:
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_service = UserService(db)
    user = await user_service.get_by_id(user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return user


async def _authenticate_api_key(key: str, db: AsyncIOMotorDatabase) -> MongoUser:
    api_key_service = ApiKeyService(db)
    user_service = UserService(db)
    
    # Get all API keys and verify
    all_keys = await api_key_service.get_all(limit=1000)
    for ak in all_keys:
        if verify_api_key(key, ak.key):
            # Update last used
            ak.last_used_at = datetime.now(timezone.utc)
            await api_key_service.update(ak.id, {"last_used_at": ak.last_used_at.isoformat()})
            
            # Get user
            user = await user_service.get_by_id(ak.user_id)
            if user and user.is_active:
                return user

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
