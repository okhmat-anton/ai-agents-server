from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from app.core.security import hash_password
from app.config import get_settings


async def create_default_admin(db: AsyncSession):
    """Create default admin user if not exists."""
    settings = get_settings()
    result = await db.execute(select(User).where(User.username == settings.DEFAULT_ADMIN_USERNAME))
    if result.scalar_one_or_none():
        return  # Already exists

    admin = User(
        username=settings.DEFAULT_ADMIN_USERNAME,
        password_hash=hash_password(settings.DEFAULT_ADMIN_PASSWORD),
        is_active=True,
    )
    db.add(admin)
    await db.commit()
