import uuid
from fastapi import Depends, HTTPException, status, Header, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.core.security import decode_token, verify_api_key
from app.models.user import User
from app.models.api_key import ApiKey
from datetime import datetime, timezone

security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
) -> User:
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
    db: AsyncSession = Depends(get_db),
) -> User:
    """Authenticate WebSocket connections via query params."""
    if api_key:
        return await _authenticate_api_key(api_key, db)
    if token:
        return await _authenticate_jwt(token, db)
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


async def _authenticate_jwt(token: str, db: AsyncSession) -> User:
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

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return user


async def _authenticate_api_key(key: str, db: AsyncSession) -> User:
    prefix = key[:8] if len(key) > 8 else key
    result = await db.execute(select(ApiKey).where(ApiKey.key_prefix == prefix))
    api_keys = result.scalars().all()

    for ak in api_keys:
        if verify_api_key(key, ak.key_hash):
            ak.last_used_at = datetime.now(timezone.utc)
            await db.flush()
            result = await db.execute(select(User).where(User.id == ak.user_id))
            user = result.scalar_one_or_none()
            if user and user.is_active:
                return user

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
