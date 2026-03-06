from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func, update
from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.agent import Agent
from app.models.log import AgentError
from app.schemas.log import AgentErrorResponse, AgentErrorResolve
from app.schemas.common import MessageResponse

# ── Per-agent errors ──
agent_error_router = APIRouter(prefix="/api/agents/{agent_id}/errors")

# ── Global errors view ──
all_errors_router = APIRouter(prefix="/api/agent-errors", tags=["agent-errors"])


@agent_error_router.get("", response_model=list[AgentErrorResponse])
async def list_agent_errors(
    agent_id: UUID,
    error_type: str | None = Query(None),
    source: str | None = Query(None),
    resolved: bool | None = Query(None),
    limit: int = Query(50, le=500),
    offset: int = Query(0, ge=0),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Agent not found")

    q = select(AgentError).where(AgentError.agent_id == agent_id)
    if error_type:
        q = q.where(AgentError.error_type == error_type)
    if source:
        q = q.where(AgentError.source == source)
    if resolved is not None:
        q = q.where(AgentError.resolved == resolved)
    q = q.order_by(AgentError.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(q)
    return result.scalars().all()


@agent_error_router.patch("/{error_id}/resolve", response_model=AgentErrorResponse)
async def resolve_agent_error(
    agent_id: UUID,
    error_id: UUID,
    body: AgentErrorResolve,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AgentError).where(AgentError.id == error_id, AgentError.agent_id == agent_id)
    )
    error = result.scalar_one_or_none()
    if not error:
        raise HTTPException(status_code=404, detail="Error not found")
    error.resolved = True
    error.resolution = body.resolution
    await db.flush()
    return error


@agent_error_router.delete("", response_model=MessageResponse)
async def clear_agent_errors(
    agent_id: UUID,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(delete(AgentError).where(AgentError.agent_id == agent_id))
    return MessageResponse(message="Agent errors cleared")


# ── Global all-agents errors ──

@all_errors_router.get("", response_model=list[AgentErrorResponse])
async def list_all_errors(
    error_type: str | None = Query(None),
    source: str | None = Query(None),
    resolved: bool | None = Query(None),
    agent_id: UUID | None = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(AgentError)
    if agent_id:
        q = q.where(AgentError.agent_id == agent_id)
    if error_type:
        q = q.where(AgentError.error_type == error_type)
    if source:
        q = q.where(AgentError.source == source)
    if resolved is not None:
        q = q.where(AgentError.resolved == resolved)
    q = q.order_by(AgentError.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(q)
    return result.scalars().all()


@all_errors_router.get("/stats")
async def error_stats(
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get error statistics grouped by agent and type."""
    total = await db.execute(select(func.count(AgentError.id)))
    unresolved = await db.execute(
        select(func.count(AgentError.id)).where(AgentError.resolved == False)
    )
    by_type = await db.execute(
        select(AgentError.error_type, func.count(AgentError.id))
        .group_by(AgentError.error_type)
    )
    by_agent = await db.execute(
        select(AgentError.agent_id, func.count(AgentError.id))
        .where(AgentError.resolved == False)
        .group_by(AgentError.agent_id)
    )
    return {
        "total": total.scalar() or 0,
        "unresolved": unresolved.scalar() or 0,
        "by_type": {row[0]: row[1] for row in by_type.all()},
        "by_agent": {str(row[0]): row[1] for row in by_agent.all()},
    }
