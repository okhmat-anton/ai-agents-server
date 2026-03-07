from motor.motor_asyncio import AsyncIOMotorDatabase
from app.mongodb.models.user import MongoUser
from app.mongodb.services import UserService
from app.core.security import hash_password
from app.config import get_settings


async def create_default_admin(db: AsyncIOMotorDatabase):
    """Create default admin user if not exists."""
    settings = get_settings()
    user_service = UserService(db)
    
    existing = await user_service.get_by_username(settings.DEFAULT_ADMIN_USERNAME)
    if existing:
        return  # Already exists

    admin = MongoUser(
        username=settings.DEFAULT_ADMIN_USERNAME,
        password_hash=hash_password(settings.DEFAULT_ADMIN_PASSWORD),
        is_active=True,
    )
    await user_service.create(admin)
