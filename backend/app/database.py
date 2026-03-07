import redis.asyncio as aioredis
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import get_settings

settings = get_settings()

redis_client: aioredis.Redis | None = None
mongodb_client: AsyncIOMotorClient | None = None
mongodb_db = None


async def init_redis():
    global redis_client
    redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)


async def get_redis() -> aioredis.Redis:
    return redis_client


async def init_mongodb():
    global mongodb_client, mongodb_db
    mongodb_client = AsyncIOMotorClient(settings.MONGODB_URL)
    # Extract database name from connection URL or use default
    db_name = settings.MONGODB_URL.split('/')[-1].split('?')[0]
    mongodb_db = mongodb_client[db_name]


def get_mongodb():
    """Get MongoDB database instance."""
    return mongodb_db


async def close_mongodb():
    global mongodb_client
    if mongodb_client:
        mongodb_client.close()
