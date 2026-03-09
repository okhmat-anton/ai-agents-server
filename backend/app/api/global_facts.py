"""
Global Facts API.

Provides a global view of all facts across all agents.
Also allows creating facts with an explicit agent_id.

Endpoints:
  GET  /api/facts         — list all facts across all agents
  POST /api/facts         — create a fact (agent_id in body)
"""
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_mongodb
from app.core.dependencies import get_current_user
from app.mongodb.services import AgentFactService, AgentService
from app.mongodb.models.agent_fact import MongoAgentFact

router = APIRouter(prefix="/api/facts", tags=["global-facts"])


# ── Schemas ──────────────────────────────────────────

class GlobalFactCreate(BaseModel):
    agent_id: str
    type: str = "fact"
    content: str
    source: str = "user"
    verified: bool = False
    confidence: float = 0.8
    tags: List[str] = []


# ── Helpers ──────────────────────────────────────────

def _fact_to_response(f: MongoAgentFact) -> dict:
    return {
        "id": f.id,
        "agent_id": f.agent_id,
        "type": f.type,
        "content": f.content,
        "source": f.source,
        "verified": f.verified,
        "confidence": f.confidence,
        "tags": f.tags,
        "created_by": f.created_by,
        "created_at": f.created_at.isoformat() if isinstance(f.created_at, datetime) else str(f.created_at),
        "updated_at": f.updated_at.isoformat() if isinstance(f.updated_at, datetime) else str(f.updated_at),
    }


# ── Endpoints ────────────────────────────────────────

@router.get("")
async def list_all_facts(
    type: Optional[str] = Query(None, description="Filter by type: fact or hypothesis"),
    verified: Optional[bool] = Query(None, description="Filter by verified status"),
    search: Optional[str] = Query(None, description="Text search in content"),
    agent_id: Optional[str] = Query(None, description="Filter by agent"),
    limit: int = Query(200, ge=1, le=500),
    skip: int = Query(0, ge=0),
    _user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """List all facts across all agents (global view). Optionally filter by agent."""
    svc = AgentFactService(db)

    if agent_id:
        # Delegate to per-agent method
        items = await svc.get_by_agent(agent_id, fact_type=type, verified=verified, limit=limit, skip=skip)
    else:
        items = await svc.get_all(fact_type=type, verified=verified, search=search, limit=limit, skip=skip)

    return {"items": [_fact_to_response(f) for f in items], "total": len(items)}


@router.post("", status_code=201)
async def create_global_fact(
    body: GlobalFactCreate,
    _user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Create a fact with an explicit agent_id."""
    # Verify agent exists
    agent = await AgentService(db).get_by_id(body.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    if body.type not in ("fact", "hypothesis"):
        raise HTTPException(status_code=400, detail="type must be 'fact' or 'hypothesis'")

    fact = MongoAgentFact(
        agent_id=body.agent_id,
        type=body.type,
        content=body.content.strip(),
        source=body.source,
        verified=body.verified,
        confidence=body.confidence,
        tags=body.tags,
        created_by="user",
    )

    svc = AgentFactService(db)
    created = await svc.create(fact)
    return _fact_to_response(created)


@router.patch("/{fact_id}")
async def update_global_fact(
    fact_id: str,
    body: dict,
    _user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Update a fact from the global view."""
    svc = AgentFactService(db)
    existing = await svc.get_by_id(fact_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Fact not found")

    update_data = {}
    for field in ("type", "content", "source", "verified", "confidence", "tags"):
        if field in body and body[field] is not None:
            update_data[field] = body[field]

    if "type" in update_data and update_data["type"] not in ("fact", "hypothesis"):
        raise HTTPException(status_code=400, detail="type must be 'fact' or 'hypothesis'")
    if "content" in update_data:
        update_data["content"] = update_data["content"].strip()

    if update_data:
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        updated = await svc.update(fact_id, update_data)
        if not updated:
            raise HTTPException(status_code=404, detail="Fact not found")
        return _fact_to_response(updated)

    return _fact_to_response(existing)


@router.delete("/{fact_id}")
async def delete_global_fact(
    fact_id: str,
    _user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Delete a fact from the global view."""
    svc = AgentFactService(db)
    existing = await svc.get_by_id(fact_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Fact not found")
    await svc.delete(fact_id)
    return {"detail": "Deleted"}
