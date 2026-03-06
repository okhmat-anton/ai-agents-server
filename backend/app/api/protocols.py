"""
Thinking Protocols API — CRUD for step-by-step agent reasoning workflows.

Protocol types:
  standard     — a regular reasoning protocol (analysis, research, etc.)
  orchestrator — a meta-protocol that selects and delegates to child protocols

Step types:
  action   — single instruction to execute
  loop     — repeat nested steps up to max_iterations
  decision — evaluate condition and optionally exit loop
  delegate — select and run a child protocol (orchestrator only)
  todo     — create a structured task list and follow it step by step
"""

import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.thinking_protocol import ThinkingProtocol

router = APIRouter(prefix="/api/protocols", tags=["thinking-protocols"], dependencies=[Depends(get_current_user)])

# ---------- Schemas ----------

STEP_TYPES = ("action", "loop", "decision", "delegate", "todo")
CATEGORIES = ("analysis", "planning", "execution", "verification", "output", "other")
PROTOCOL_TYPES = ("standard", "orchestrator", "loop")


class StepBase(BaseModel):
    id: str | None = None
    type: Literal["action", "loop", "decision", "delegate", "todo"] = "action"
    name: str = ""
    instruction: str = ""
    category: str = "other"
    # loop-specific
    max_iterations: int | None = None
    exit_condition: str | None = None
    steps: list["StepBase"] = []     # nested steps for loops
    # delegate-specific
    protocol_ids: list[str] = []     # candidate child protocol IDs to choose from

StepBase.model_rebuild()


class ProtocolCreate(BaseModel):
    name: str
    description: str = ""
    type: str = "standard"  # standard, orchestrator
    steps: list[StepBase] = []


class ProtocolUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    type: str | None = None
    steps: list[StepBase] | None = None


class ProtocolResponse(BaseModel):
    id: str
    name: str
    description: str
    type: str
    steps: list
    is_default: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------- Helpers ----------

def _assign_ids(steps: list[dict], prefix: str = "s") -> list[dict]:
    """Ensure every step has a unique id."""
    for i, step in enumerate(steps):
        if not step.get("id"):
            step["id"] = f"{prefix}_{i}_{uuid.uuid4().hex[:6]}"
        if step.get("steps"):
            step["steps"] = _assign_ids(step["steps"], prefix=step["id"])
    return steps


def _to_response(p: ThinkingProtocol) -> dict:
    return {
        "id": str(p.id),
        "name": p.name,
        "description": p.description or "",
        "type": p.type or "standard",
        "steps": p.steps or [],
        "is_default": p.is_default,
        "created_at": p.created_at,
        "updated_at": p.updated_at,
    }


# ---------- Endpoints ----------

@router.get("")
async def list_protocols(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ThinkingProtocol).order_by(ThinkingProtocol.is_default.desc(), ThinkingProtocol.name))
    protos = result.scalars().all()
    return [_to_response(p) for p in protos]


@router.get("/{protocol_id}")
async def get_protocol(protocol_id: str, db: AsyncSession = Depends(get_db)):
    p = await db.get(ThinkingProtocol, protocol_id)
    if not p:
        raise HTTPException(404, "Protocol not found")
    return _to_response(p)


@router.post("", status_code=201)
async def create_protocol(body: ProtocolCreate, db: AsyncSession = Depends(get_db)):
    steps_raw = [s.model_dump() for s in body.steps]
    steps_raw = _assign_ids(steps_raw)
    p = ThinkingProtocol(
        name=body.name,
        description=body.description,
        type=body.type if body.type in PROTOCOL_TYPES else "standard",
        steps=steps_raw,
    )
    db.add(p)
    await db.flush()
    await db.refresh(p)
    return _to_response(p)


@router.put("/{protocol_id}")
async def update_protocol(protocol_id: str, body: ProtocolUpdate, db: AsyncSession = Depends(get_db)):
    p = await db.get(ThinkingProtocol, protocol_id)
    if not p:
        raise HTTPException(404, "Protocol not found")
    if body.name is not None:
        p.name = body.name
    if body.description is not None:
        p.description = body.description
    if body.type is not None and body.type in PROTOCOL_TYPES:
        p.type = body.type
    if body.steps is not None:
        steps_raw = [s.model_dump() for s in body.steps]
        steps_raw = _assign_ids(steps_raw)
        p.steps = steps_raw
    p.updated_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(p)
    return _to_response(p)


@router.delete("/{protocol_id}", status_code=204)
async def delete_protocol(protocol_id: str, db: AsyncSession = Depends(get_db)):
    p = await db.get(ThinkingProtocol, protocol_id)
    if not p:
        raise HTTPException(404, "Protocol not found")
    if p.is_default:
        raise HTTPException(400, "Cannot delete the default protocol")
    await db.delete(p)
    return None


@router.post("/{protocol_id}/duplicate")
async def duplicate_protocol(protocol_id: str, db: AsyncSession = Depends(get_db)):
    p = await db.get(ThinkingProtocol, protocol_id)
    if not p:
        raise HTTPException(404, "Protocol not found")
    new = ThinkingProtocol(
        name=f"{p.name} (copy)",
        description=p.description,
        type=p.type,
        steps=p.steps,
        is_default=False,
    )
    db.add(new)
    await db.flush()
    await db.refresh(new)
    return _to_response(new)
