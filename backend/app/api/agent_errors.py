from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.database import get_mongodb
from app.core.dependencies import get_current_user
from app.mongodb.services import AgentService, AgentErrorService
from app.schemas.log import AgentErrorResponse, AgentErrorResolve
from app.schemas.common import MessageResponse

# ── Per-agent errors ──
agent_error_router = APIRouter(prefix="/api/agents/{agent_id}/errors")

# ── Global errors view ──
all_errors_router = APIRouter(prefix="/api/agent-errors", tags=["agent-errors"])


def _error_to_dict(err) -> dict:
    """Convert MongoAgentError to response-compatible dict."""
    return {
        "id": err.id,
        "agent_id": err.agent_id,
        "error_type": err.error_type,
        "source": err.source,
        "message": err.message,
        "context": err.context,
        "resolved": err.resolved,
        "resolution": err.resolution,
        "created_at": err.created_at,
    }


@agent_error_router.get("", response_model=list[AgentErrorResponse])
async def list_agent_errors(
    agent_id: UUID,
    error_type: str | None = Query(None),
    source: str | None = Query(None),
    resolved: bool | None = Query(None),
    limit: int = Query(50, le=500),
    offset: int = Query(0, ge=0),
    _user = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    agent = await AgentService(db).get_by_id(str(agent_id))
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    svc = AgentErrorService(db)
    filt: dict = {"agent_id": str(agent_id)}
    if error_type:
        filt["error_type"] = error_type
    if source:
        filt["source"] = source
    if resolved is not None:
        filt["resolved"] = resolved

    errors = await svc.get_all(filter=filt, skip=offset, limit=limit)
    errors.sort(key=lambda e: e.created_at, reverse=True)
    return [_error_to_dict(e) for e in errors]


@agent_error_router.patch("/{error_id}/resolve", response_model=AgentErrorResponse)
async def resolve_agent_error(
    agent_id: UUID,
    error_id: UUID,
    body: AgentErrorResolve,
    _user = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    svc = AgentErrorService(db)
    error = await svc.get_by_id(str(error_id))
    if not error or error.agent_id != str(agent_id):
        raise HTTPException(status_code=404, detail="Error not found")
    updated = await svc.update(str(error_id), {"resolved": True, "resolution": body.resolution})
    return _error_to_dict(updated)


@agent_error_router.delete("", response_model=MessageResponse)
async def clear_agent_errors(
    agent_id: UUID,
    _user = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    await AgentErrorService(db).delete_by_agent(str(agent_id))
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
    _user = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    svc = AgentErrorService(db)
    filt: dict = {}
    if agent_id:
        filt["agent_id"] = str(agent_id)
    if error_type:
        filt["error_type"] = error_type
    if source:
        filt["source"] = source
    if resolved is not None:
        filt["resolved"] = resolved

    errors = await svc.get_all(filter=filt, skip=offset, limit=limit)
    errors.sort(key=lambda e: e.created_at, reverse=True)
    return [_error_to_dict(e) for e in errors]


@all_errors_router.get("/stats")
async def error_stats(
    _user = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Get error statistics grouped by agent and type."""
    svc = AgentErrorService(db)
    total = await svc.count()
    unresolved = await svc.count({"resolved": False})

    # by_type — aggregate manually
    all_errors = await svc.get_all(limit=10000)
    by_type: dict[str, int] = {}
    by_agent: dict[str, int] = {}
    for e in all_errors:
        by_type[e.error_type] = by_type.get(e.error_type, 0) + 1
        if not e.resolved:
            by_agent[e.agent_id] = by_agent.get(e.agent_id, 0) + 1

    return {
        "total": total,
        "unresolved": unresolved,
        "by_type": by_type,
        "by_agent": by_agent,
    }
