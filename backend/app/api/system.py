import time
from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timezone, timedelta
from app.database import get_mongodb
from app import database as _db
from app.core.dependencies import get_current_user
from app.mongodb.services import (
    AgentService, TaskService, SkillService, MemoryService,
)
from app.schemas.common import MessageResponse, HealthResponse, SystemStatsResponse
from app.config import get_settings
from app.services.log_service import read_system_logs, clear_old_system_logs
import httpx

router = APIRouter(prefix="/api/system", tags=["system"])
_start_time = time.time()


@router.get("/health", response_model=HealthResponse)
async def health(db: AsyncIOMotorDatabase = Depends(get_mongodb)):
    settings = get_settings()

    # Check MongoDB
    db_status = "ok"
    try:
        await db.command("ping")
    except Exception:
        db_status = "error"

    # Check Redis
    redis_status = "ok"
    try:
        if _db.redis_client:
            await _db.redis_client.ping()
        else:
            redis_status = "not connected"
    except Exception:
        redis_status = "error"

    # Check ChromaDB
    chromadb_status = "ok"
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get(f"{settings.CHROMADB_URL}/api/v2/heartbeat")
            if r.status_code != 200:
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
    _user = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    total_agents = await AgentService(db).count()
    running_agents = await AgentService(db).count(filter={"status": "running"})
    total_tasks = await TaskService(db).count()
    pending_tasks = await TaskService(db).count(filter={"status": "pending"})
    total_skills = await SkillService(db).count()
    total_memories = await MemoryService(db).count()

    # Count system log lines from file
    total_system_logs = 0
    try:
        logs = await read_system_logs(limit=0)  # just to get count
        total_system_logs = len(logs) if logs else 0
    except Exception:
        pass

    return SystemStatsResponse(
        total_agents=total_agents,
        running_agents=running_agents,
        total_tasks=total_tasks,
        pending_tasks=pending_tasks,
        total_skills=total_skills,
        total_memories=total_memories,
        total_system_logs=total_system_logs,
    )


@router.get("/logs")
async def list_system_logs(
    level: str | None = Query(None),
    source: str | None = Query(None),
    search: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    limit: int = Query(50, le=500),
    offset: int = Query(0, ge=0),
    _user = Depends(get_current_user),
):
    logs = await read_system_logs(limit=limit + offset + 500)

    # Apply filters
    filtered = []
    for log in logs:
        if level and log.get("level") != level:
            continue
        if source and log.get("source") != source:
            continue
        if search and search.lower() not in log.get("message", "").lower():
            continue
        if date_from:
            ts = log.get("timestamp", "")
            if ts and ts < date_from.isoformat():
                continue
        if date_to:
            ts = log.get("timestamp", "")
            if ts and ts > date_to.isoformat():
                continue
        filtered.append(log)

    # Sort by timestamp descending
    filtered.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    # Apply pagination
    return filtered[offset:offset + limit]


@router.delete("/logs", response_model=MessageResponse)
async def clear_system_logs_endpoint(
    days: int = Query(30, description="Delete logs older than N days"),
    _user = Depends(get_current_user),
):
    removed = await clear_old_system_logs(days)
    return MessageResponse(message=f"Logs older than {days} days deleted ({removed} removed)")
