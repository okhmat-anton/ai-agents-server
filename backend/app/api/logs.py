from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timezone
from app.database import get_mongodb
from app.core.dependencies import get_current_user
from app.mongodb.services import AgentService, AgentLogService
from app.schemas.log import AgentLogResponse
from app.schemas.common import MessageResponse

router = APIRouter(tags=["logs"])

# ------- Agent Logs -------
agent_log_router = APIRouter(prefix="/api/agents/{agent_id}/logs")


@agent_log_router.get("", response_model=list[AgentLogResponse])
async def list_agent_logs(
    agent_id: UUID,
    level: str | None = Query(None),
    search: str | None = Query(None),
    limit: int = Query(50, le=500),
    offset: int = Query(0, ge=0),
    _user = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    agent = await AgentService(db).get_by_id(str(agent_id))
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    svc = AgentLogService(db)
    filt: dict = {"agent_id": str(agent_id)}
    if level:
        filt["level"] = level

    logs = await svc.get_all(filter=filt, skip=offset, limit=limit)

    if search:
        search_lower = search.lower()
        logs = [lg for lg in logs if search_lower in lg.message.lower()]

    logs.sort(key=lambda l: l.created_at, reverse=True)
    return [
        {"id": lg.id, "agent_id": lg.agent_id, "level": lg.level,
         "message": lg.message, "metadata_": lg.metadata_, "created_at": lg.created_at}
        for lg in logs
    ]


@agent_log_router.delete("", response_model=MessageResponse)
async def clear_agent_logs(
    agent_id: UUID,
    _user = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    await AgentLogService(db).delete_by_agent(str(agent_id))
    return MessageResponse(message="Agent logs cleared")
