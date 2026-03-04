from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from datetime import datetime, timezone
from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.agent import Agent
from app.models.log import SystemLog, AgentLog
from app.schemas.log import SystemLogResponse, AgentLogResponse
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
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Agent not found")

    q = select(AgentLog).where(AgentLog.agent_id == agent_id)
    if level:
        q = q.where(AgentLog.level == level)
    if search:
        q = q.where(AgentLog.message.ilike(f"%{search}%"))
    q = q.order_by(AgentLog.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(q)
    return result.scalars().all()


@agent_log_router.delete("", response_model=MessageResponse)
async def clear_agent_logs(
    agent_id: UUID,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(delete(AgentLog).where(AgentLog.agent_id == agent_id))
    return MessageResponse(message="Agent logs cleared")
