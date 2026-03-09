"""
Agent Events API.

Agents store events in memory — things that happened, observations,
discoveries, decisions, milestones. Each event belongs to a specific
agent and can be managed via UI or agent skills.

Endpoints:
  GET    /api/agents/{agent_id}/events         — list all events
  POST   /api/agents/{agent_id}/events         — create an event
  PATCH  /api/agents/{agent_id}/events/{id}    — update an event
  DELETE /api/agents/{agent_id}/events/{id}    — delete an event
"""
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_mongodb
from app.core.dependencies import get_current_user
from app.mongodb.services import AgentService, AgentEventService
from app.mongodb.models.agent_event import MongoAgentEvent

router = APIRouter(prefix="/api/agents", tags=["agent-events"])


# ── Schemas ──────────────────────────────────────────

class EventCreate(BaseModel):
    event_type: str = "observation"  # conversation, observation, discovery, decision, milestone, custom
    title: str
    description: str = ""
    source: str = "user"
    importance: str = "medium"  # low, medium, high, critical
    tags: List[str] = []
    event_date: Optional[str] = None  # ISO datetime string; defaults to now


class EventUpdate(BaseModel):
    event_type: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    source: Optional[str] = None
    importance: Optional[str] = None
    tags: Optional[List[str]] = None
    event_date: Optional[str] = None


class EventResponse(BaseModel):
    id: str
    agent_id: str
    event_type: str
    title: str
    description: str
    source: str
    importance: str
    tags: List[str]
    created_by: str
    event_date: str
    created_at: str
    updated_at: str


# ── Helpers ──────────────────────────────────────────

VALID_EVENT_TYPES = {"conversation", "observation", "discovery", "decision", "milestone", "custom"}
VALID_IMPORTANCE = {"low", "medium", "high", "critical"}


async def _get_agent_or_404(agent_id: str, db: AsyncIOMotorDatabase):
    agent = await AgentService(db).get_by_id(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


def _event_to_response(e: MongoAgentEvent) -> dict:
    return {
        "id": e.id,
        "agent_id": e.agent_id,
        "event_type": e.event_type,
        "title": e.title,
        "description": e.description,
        "source": e.source,
        "importance": e.importance,
        "tags": e.tags,
        "created_by": e.created_by,
        "event_date": e.event_date.isoformat() if isinstance(e.event_date, datetime) else str(e.event_date),
        "created_at": e.created_at.isoformat() if isinstance(e.created_at, datetime) else str(e.created_at),
        "updated_at": e.updated_at.isoformat() if isinstance(e.updated_at, datetime) else str(e.updated_at),
    }


# ── Endpoints ────────────────────────────────────────

@router.get("/{agent_id}/events")
async def list_events(
    agent_id: str,
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    importance: Optional[str] = Query(None, description="Filter by importance"),
    search: Optional[str] = Query(None, description="Text search in title/description"),
    limit: int = Query(200, ge=1, le=500),
    skip: int = Query(0, ge=0),
    _user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """List all events for an agent."""
    await _get_agent_or_404(agent_id, db)
    svc = AgentEventService(db)

    if search:
        items = await svc.search_by_text(agent_id, search, limit=limit)
    else:
        items = await svc.get_by_agent(agent_id, event_type=event_type, importance=importance, limit=limit, skip=skip)

    return {
        "items": [_event_to_response(e) for e in items],
        "total": len(items),
    }


@router.post("/{agent_id}/events", status_code=201)
async def create_event(
    agent_id: str,
    body: EventCreate,
    _user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Create a new event."""
    await _get_agent_or_404(agent_id, db)

    if body.event_type not in VALID_EVENT_TYPES:
        raise HTTPException(status_code=400, detail=f"event_type must be one of: {', '.join(VALID_EVENT_TYPES)}")
    if body.importance not in VALID_IMPORTANCE:
        raise HTTPException(status_code=400, detail=f"importance must be one of: {', '.join(VALID_IMPORTANCE)}")

    event_date = datetime.now(timezone.utc)
    if body.event_date:
        try:
            event_date = datetime.fromisoformat(body.event_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid event_date format (expected ISO 8601)")

    event = MongoAgentEvent(
        agent_id=agent_id,
        event_type=body.event_type,
        title=body.title.strip(),
        description=body.description.strip() if body.description else "",
        source=body.source,
        importance=body.importance,
        tags=body.tags,
        created_by="user",
        event_date=event_date,
    )

    svc = AgentEventService(db)
    created = await svc.create(event)
    return _event_to_response(created)


@router.patch("/{agent_id}/events/{event_id}")
async def update_event(
    agent_id: str,
    event_id: str,
    body: EventUpdate,
    _user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Update an event."""
    await _get_agent_or_404(agent_id, db)
    svc = AgentEventService(db)
    existing = await svc.get_by_id(event_id)
    if not existing or existing.agent_id != agent_id:
        raise HTTPException(status_code=404, detail="Event not found")

    update_data = {}
    if body.event_type is not None:
        if body.event_type not in VALID_EVENT_TYPES:
            raise HTTPException(status_code=400, detail=f"event_type must be one of: {', '.join(VALID_EVENT_TYPES)}")
        update_data["event_type"] = body.event_type
    if body.title is not None:
        update_data["title"] = body.title.strip()
    if body.description is not None:
        update_data["description"] = body.description.strip()
    if body.source is not None:
        update_data["source"] = body.source
    if body.importance is not None:
        if body.importance not in VALID_IMPORTANCE:
            raise HTTPException(status_code=400, detail=f"importance must be one of: {', '.join(VALID_IMPORTANCE)}")
        update_data["importance"] = body.importance
    if body.tags is not None:
        update_data["tags"] = body.tags
    if body.event_date is not None:
        try:
            update_data["event_date"] = datetime.fromisoformat(body.event_date).isoformat()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid event_date format")

    if update_data:
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        updated = await svc.update(event_id, update_data)
        if not updated:
            raise HTTPException(status_code=404, detail="Event not found")
        return _event_to_response(updated)

    return _event_to_response(existing)


@router.delete("/{agent_id}/events/{event_id}")
async def delete_event(
    agent_id: str,
    event_id: str,
    _user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Delete an event."""
    await _get_agent_or_404(agent_id, db)
    svc = AgentEventService(db)
    existing = await svc.get_by_id(event_id)
    if not existing or existing.agent_id != agent_id:
        raise HTTPException(status_code=404, detail="Event not found")

    await svc.delete(event_id)
    return {"detail": "Deleted"}
