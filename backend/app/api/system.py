import time
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from datetime import datetime, timezone, timedelta
from app.database import get_db, redis_client
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.agent import Agent
from app.models.task import Task
from app.models.log import SystemLog
from app.models.skill import Skill
from app.models.memory import Memory
from app.schemas.log import SystemLogResponse
from app.schemas.common import MessageResponse, HealthResponse, SystemStatsResponse
from app.config import get_settings
import httpx

router = APIRouter(prefix="/api/system", tags=["system"])
_start_time = time.time()


@router.get("/health", response_model=HealthResponse)
async def health(db: AsyncSession = Depends(get_db)):
    settings = get_settings()

    # Check DB
    db_status = "ok"
    try:
        await db.execute(select(func.now()))
    except Exception:
        db_status = "error"

    # Check Redis
    redis_status = "ok"
    try:
        if redis_client:
            await redis_client.ping()
        else:
            redis_status = "not connected"
    except Exception:
        redis_status = "error"

    # Check ChromaDB
    chromadb_status = "ok"
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get(f"{settings.CHROMADB_URL}/api/v1/heartbeat")
            if r.status_code != 200:
                chromadb_status = "error"
    except Exception:
        chromadb_status = "unavailable"

    # Check Ollama
    ollama_status = "ok"
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            if r.status_code != 200:
                ollama_status = "error"
    except Exception:
        ollama_status = "unavailable"

    return HealthResponse(
        status="ok" if db_status == "ok" else "degraded",
        database=db_status,
        redis=redis_status,
        chromadb=chromadb_status,
        ollama=ollama_status,
        uptime_seconds=round(time.time() - _start_time, 2),
    )


@router.get("/stats", response_model=SystemStatsResponse)
async def stats(
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    total_agents = (await db.execute(select(func.count(Agent.id)))).scalar() or 0
    running_agents = (await db.execute(select(func.count(Agent.id)).where(Agent.status == "running"))).scalar() or 0
    total_tasks = (await db.execute(select(func.count(Task.id)))).scalar() or 0
    pending_tasks = (await db.execute(select(func.count(Task.id)).where(Task.status == "pending"))).scalar() or 0
    total_skills = (await db.execute(select(func.count(Skill.id)))).scalar() or 0
    total_memories = (await db.execute(select(func.count(Memory.id)))).scalar() or 0
    total_system_logs = (await db.execute(select(func.count(SystemLog.id)))).scalar() or 0

    return SystemStatsResponse(
        total_agents=total_agents,
        running_agents=running_agents,
        total_tasks=total_tasks,
        pending_tasks=pending_tasks,
        total_skills=total_skills,
        total_memories=total_memories,
        total_system_logs=total_system_logs,
    )


@router.get("/logs", response_model=list[SystemLogResponse])
async def list_system_logs(
    level: str | None = Query(None),
    source: str | None = Query(None),
    search: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    limit: int = Query(50, le=500),
    offset: int = Query(0, ge=0),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(SystemLog)
    if level:
        q = q.where(SystemLog.level == level)
    if source:
        q = q.where(SystemLog.source == source)
    if search:
        q = q.where(SystemLog.message.ilike(f"%{search}%"))
    if date_from:
        q = q.where(SystemLog.created_at >= date_from)
    if date_to:
        q = q.where(SystemLog.created_at <= date_to)
    q = q.order_by(SystemLog.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(q)
    return result.scalars().all()


@router.delete("/logs", response_model=MessageResponse)
async def clear_system_logs(
    days: int = Query(30, description="Delete logs older than N days"),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    await db.execute(delete(SystemLog).where(SystemLog.created_at < cutoff))
    return MessageResponse(message=f"Logs older than {days} days deleted")
