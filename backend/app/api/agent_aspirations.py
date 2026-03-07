"""
Agent Aspirations API — filesystem-based dreams, desires & goals for agents.

Each agent has an aspirations.json file in their directory containing:
  - dreams: long-term visions, abstract aspirations
  - desires: things the agent wants to have / experience / achieve
  - goals: concrete, actionable objectives (may have status & deadline)

Each item has a `locked` flag:
  - locked=true  → created by user, agent CANNOT modify or delete
  - locked=false → created by agent (or user chose "unlockable"), agent CAN modify
  Agent may create new items but they must not contradict locked ones.

File structure (aspirations.json):
{
  "dreams":  [ {"id": "dr_xxx", "text": "...", "locked": true, "priority": "high",
                "created_by": "user", "created_at": "..."} ],
  "desires": [ {"id": "des_xxx", "text": "...", "locked": false, "priority": "medium",
                "created_by": "agent", "created_at": "..."} ],
  "goals":   [ {"id": "goal_xxx", "text": "...", "locked": true, "priority": "high",
                "status": "active", "deadline": null,
                "created_by": "user", "created_at": "..."} ]
}
"""
import json
import uuid as _uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import get_settings
from app.database import get_mongodb
from app.core.dependencies import get_current_user
from app.mongodb.services import AgentService

router = APIRouter(prefix="/api/agents", tags=["agent-aspirations"])
settings = get_settings()

ASPIRATION_TYPES = ("dreams", "desires", "goals")
PRIORITIES = ("low", "medium", "high")
GOAL_STATUSES = ("active", "in_progress", "completed", "abandoned")


# ── Schemas ──────────────────────────────────────────

class AspirationCreate(BaseModel):
    text: str
    priority: str = "medium"
    locked: bool = True          # default: user-created → locked
    # goals only
    status: str | None = None    # active / in_progress / completed / abandoned
    deadline: str | None = None  # ISO date string


class AspirationUpdate(BaseModel):
    text: str | None = None
    priority: str | None = None
    locked: bool | None = None
    status: str | None = None
    deadline: str | None = None


class AspirationResponse(BaseModel):
    id: str
    text: str
    type: str          # dreams / desires / goals
    priority: str
    locked: bool
    created_by: str
    created_at: str
    # goals only
    status: str | None = None
    deadline: str | None = None


class AspirationsListResponse(BaseModel):
    dreams: list[AspirationResponse]
    desires: list[AspirationResponse]
    goals: list[AspirationResponse]
    total: int


# ── File helpers ─────────────────────────────────────

def _get_agent_dir(agent_name: str) -> Path:
    base = Path(settings.AGENTS_DIR).resolve()
    agent_dir = (base / agent_name).resolve()
    if not str(agent_dir).startswith(str(base)):
        raise HTTPException(status_code=400, detail="Invalid agent name")
    return agent_dir


def _aspirations_path(agent_name: str) -> Path:
    return _get_agent_dir(agent_name) / "aspirations.json"


def read_aspirations(agent_name: str) -> dict:
    """Read aspirations.json — returns {"dreams": [...], "desires": [...], "goals": [...]}."""
    path = _aspirations_path(agent_name)
    if not path.exists():
        return {"dreams": [], "desires": [], "goals": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {
            "dreams": data.get("dreams", []),
            "desires": data.get("desires", []),
            "goals": data.get("goals", []),
        }
    except (json.JSONDecodeError, OSError):
        return {"dreams": [], "desires": [], "goals": []}


def write_aspirations(agent_name: str, data: dict):
    """Write aspirations.json."""
    path = _aspirations_path(agent_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{_uuid.uuid4().hex[:8]}"


async def _get_agent_or_404(agent_id, db: AsyncIOMotorDatabase):
    agent = await AgentService(db).get_by_id(str(agent_id))
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


def _format_item(item: dict, aspiration_type: str) -> dict:
    base = {
        "id": item.get("id", ""),
        "text": item.get("text", ""),
        "type": aspiration_type,
        "priority": item.get("priority", "medium"),
        "locked": item.get("locked", False),
        "created_by": item.get("created_by", "user"),
        "created_at": item.get("created_at", ""),
    }
    if aspiration_type == "goals":
        base["status"] = item.get("status", "active")
        base["deadline"] = item.get("deadline")
    return base


def init_aspirations_file(agent_name: str):
    """Create empty aspirations.json if doesn't exist."""
    path = _aspirations_path(agent_name)
    if not path.exists():
        write_aspirations(agent_name, {"dreams": [], "desires": [], "goals": []})


# ── Endpoints ────────────────────────────────────────

@router.get("/{agent_id}/aspirations")
async def list_aspirations(
    agent_id: str,
    _user = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Get all aspirations for an agent."""
    agent = await _get_agent_or_404(agent_id, db)
    data = read_aspirations(agent.name)

    dreams = [_format_item(d, "dreams") for d in data["dreams"]]
    desires = [_format_item(d, "desires") for d in data["desires"]]
    goals = [_format_item(g, "goals") for g in data["goals"]]

    return {
        "dreams": dreams,
        "desires": desires,
        "goals": goals,
        "total": len(dreams) + len(desires) + len(goals),
    }


@router.post("/{agent_id}/aspirations/{aspiration_type}")
async def add_aspiration(
    agent_id: str,
    aspiration_type: str,
    body: AspirationCreate,
    _user = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Add a dream, desire, or goal."""
    if aspiration_type not in ASPIRATION_TYPES:
        raise HTTPException(status_code=400, detail=f"type must be one of: {', '.join(ASPIRATION_TYPES)}")

    agent = await _get_agent_or_404(agent_id, db)
    data = read_aspirations(agent.name)

    prefix_map = {"dreams": "dr", "desires": "des", "goals": "goal"}
    item = {
        "id": _new_id(prefix_map[aspiration_type]),
        "text": body.text.strip(),
        "priority": body.priority if body.priority in PRIORITIES else "medium",
        "locked": body.locked,
        "created_by": "user",
        "created_at": _now_iso(),
    }

    if aspiration_type == "goals":
        item["status"] = body.status if body.status in GOAL_STATUSES else "active"
        item["deadline"] = body.deadline

    data[aspiration_type].append(item)
    write_aspirations(agent.name, data)

    return _format_item(item, aspiration_type)


@router.put("/{agent_id}/aspirations/{aspiration_type}/{item_id}")
async def update_aspiration(
    agent_id: str,
    aspiration_type: str,
    item_id: str,
    body: AspirationUpdate,
    _user = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Update a dream, desire, or goal."""
    if aspiration_type not in ASPIRATION_TYPES:
        raise HTTPException(status_code=400, detail=f"type must be one of: {', '.join(ASPIRATION_TYPES)}")

    agent = await _get_agent_or_404(agent_id, db)
    data = read_aspirations(agent.name)

    for item in data[aspiration_type]:
        if item["id"] == item_id:
            if body.text is not None:
                item["text"] = body.text.strip()
            if body.priority is not None and body.priority in PRIORITIES:
                item["priority"] = body.priority
            if body.locked is not None:
                item["locked"] = body.locked
            if aspiration_type == "goals":
                if body.status is not None and body.status in GOAL_STATUSES:
                    item["status"] = body.status
                if body.deadline is not None:
                    item["deadline"] = body.deadline
            write_aspirations(agent.name, data)
            return _format_item(item, aspiration_type)

    raise HTTPException(status_code=404, detail=f"{aspiration_type[:-1].capitalize()} not found")


@router.delete("/{agent_id}/aspirations/{aspiration_type}/{item_id}")
async def delete_aspiration(
    agent_id: str,
    aspiration_type: str,
    item_id: str,
    _user = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Delete a dream, desire, or goal."""
    if aspiration_type not in ASPIRATION_TYPES:
        raise HTTPException(status_code=400, detail=f"type must be one of: {', '.join(ASPIRATION_TYPES)}")

    agent = await _get_agent_or_404(agent_id, db)
    data = read_aspirations(agent.name)

    original_len = len(data[aspiration_type])
    data[aspiration_type] = [i for i in data[aspiration_type] if i["id"] != item_id]
    if len(data[aspiration_type]) == original_len:
        raise HTTPException(status_code=404, detail=f"{aspiration_type[:-1].capitalize()} not found")

    write_aspirations(agent.name, data)
    return {"message": f"{aspiration_type[:-1].capitalize()} deleted"}


# ── Reorder ──────────────────────────────────────────

@router.post("/{agent_id}/aspirations/reorder")
async def reorder_aspirations(
    agent_id: str,
    body: dict,
    _user = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Reorder items. Body: {"type": "dreams"|"desires"|"goals", "ids": ["id1", ...]}"""
    agent = await _get_agent_or_404(agent_id, db)
    data = read_aspirations(agent.name)

    aspiration_type = body.get("type", "goals")
    new_order = body.get("ids", [])

    if aspiration_type not in ASPIRATION_TYPES:
        raise HTTPException(status_code=400, detail=f"type must be one of: {', '.join(ASPIRATION_TYPES)}")

    items_list = data[aspiration_type]
    by_id = {i["id"]: i for i in items_list}

    reordered = []
    for iid in new_order:
        if iid in by_id:
            reordered.append(by_id.pop(iid))
    reordered.extend(by_id.values())

    data[aspiration_type] = reordered
    write_aspirations(agent.name, data)

    return {"message": "Reordered"}
