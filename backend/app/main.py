from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.database import init_db, init_redis, async_session
from app.services.auth_service import create_default_admin
from app.services.skill_service import create_system_skills
from app.services.model_service import sync_ollama_models

from app.api.auth import router as auth_router
from app.api.settings import router as settings_router
from app.api.agents import router as agents_router
from app.api.tasks import common_router as tasks_router, agent_task_router
from app.api.skills import router as skills_router, agent_skill_router
from app.api.logs import agent_log_router
from app.api.system import router as system_router
from app.api.memory import router as memory_router
from app.api.websocket import router as ws_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_redis()
    await init_db()

    # Create default admin & system skills
    async with async_session() as db:
        await create_default_admin(db)
        await create_system_skills(db)
        await sync_ollama_models(db)

    yield

    # Shutdown
    pass


app = FastAPI(
    title=settings.APP_TITLE,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/api/system/openapi.json",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(settings_router)
app.include_router(agents_router)
app.include_router(tasks_router)
app.include_router(agent_task_router)
app.include_router(skills_router)
app.include_router(agent_skill_router)
app.include_router(agent_log_router)
app.include_router(system_router)
app.include_router(memory_router)
app.include_router(ws_router)


@app.get("/")
async def root():
    return {"message": settings.APP_TITLE, "version": settings.APP_VERSION, "docs": "/docs"}
