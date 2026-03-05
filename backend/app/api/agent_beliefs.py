"""
Agent Beliefs API — filesystem-based belief system for agents.

Each agent has a beliefs.json file in their directory containing:
  - core: list of immutable base beliefs (set by user, cannot be edited by agent)
  - additional: list of mutable beliefs (can be created/edited/deleted by agent or user)

Core beliefs have higher weight; additional beliefs cannot override them.

File structure (beliefs.json):
{
  "core": [
    {"id": "c1", "text": "...", "category": "moral", "created_at": "..."}
  ],
  "additional": [
    {"id": "a1", "text": "...", "category": "preference", "weight": 0.5, "created_at": "...", "created_by": "user|agent"}
  ]
}
"""
import json
import uuid as _uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import get_settings
from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.agent import Agent

router = APIRouter(prefix="/api/agents", tags=["agent-beliefs"])
settings = get_settings()

BELIEF_CATEGORIES = ["moral", "behavioral", "communication", "restriction", "preference", "goal", "other"]


# ── Schemas ──────────────────────────────────────────

class BeliefCreate(BaseModel):
    text: str
    category: str = "other"


class BeliefUpdate(BaseModel):
    text: str | None = None
    category: str | None = None
    weight: float | None = None


class BeliefResponse(BaseModel):
    id: str
    text: str
    category: str
    weight: float = 1.0
    is_core: bool = False
    created_at: str
    created_by: str = "user"


class BeliefsListResponse(BaseModel):
    core: list[BeliefResponse]
    additional: list[BeliefResponse]
    total: int


# ── File helpers ─────────────────────────────────────

def _get_agent_dir(agent_name: str) -> Path:
    base = Path(settings.AGENTS_DIR).resolve()
    agent_dir = (base / agent_name).resolve()
    if not str(agent_dir).startswith(str(base)):
        raise HTTPException(status_code=400, detail="Invalid agent name")
    return agent_dir


def _beliefs_path(agent_name: str) -> Path:
    return _get_agent_dir(agent_name) / "beliefs.json"


def read_beliefs(agent_name: str) -> dict:
    """Read beliefs.json — returns {"core": [...], "additional": [...]}."""
    path = _beliefs_path(agent_name)
    if not path.exists():
        return {"core": [], "additional": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {
            "core": data.get("core", []),
            "additional": data.get("additional", []),
        }
    except (json.JSONDecodeError, OSError):
        return {"core": [], "additional": []}


def write_beliefs(agent_name: str, data: dict):
    """Write beliefs.json."""
    path = _beliefs_path(agent_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str = "b") -> str:
    return f"{prefix}_{_uuid.uuid4().hex[:8]}"


async def _get_agent_or_404(agent_id, db: AsyncSession) -> Agent:
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


def _format_belief(b: dict, is_core: bool) -> dict:
    return {
        "id": b.get("id", ""),
        "text": b.get("text", ""),
        "category": b.get("category", "other"),
        "weight": 1.0 if is_core else b.get("weight", 0.5),
        "is_core": is_core,
        "created_at": b.get("created_at", ""),
        "created_by": "system" if is_core else b.get("created_by", "user"),
    }


def init_beliefs_file(agent_name: str):
    """Create empty beliefs.json if doesn't exist."""
    path = _beliefs_path(agent_name)
    if not path.exists():
        write_beliefs(agent_name, {"core": [], "additional": []})


# ── Endpoints ────────────────────────────────────────

@router.get("/{agent_id}/beliefs")
async def list_beliefs(
    agent_id: str,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all beliefs (core + additional) for an agent."""
    agent = await _get_agent_or_404(agent_id, db)
    data = read_beliefs(agent.name)

    core = [_format_belief(b, is_core=True) for b in data["core"]]
    additional = [_format_belief(b, is_core=False) for b in data["additional"]]

    return {
        "core": core,
        "additional": additional,
        "total": len(core) + len(additional),
    }


# ── Core beliefs (user-only) ────────────────────────

@router.post("/{agent_id}/beliefs/core")
async def add_core_belief(
    agent_id: str,
    body: BeliefCreate,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a core belief. Only users can manage core beliefs."""
    agent = await _get_agent_or_404(agent_id, db)
    data = read_beliefs(agent.name)

    belief = {
        "id": _new_id("core"),
        "text": body.text.strip(),
        "category": body.category if body.category in BELIEF_CATEGORIES else "other",
        "created_at": _now_iso(),
    }
    data["core"].append(belief)
    write_beliefs(agent.name, data)

    return _format_belief(belief, is_core=True)


@router.put("/{agent_id}/beliefs/core/{belief_id}")
async def update_core_belief(
    agent_id: str,
    belief_id: str,
    body: BeliefUpdate,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a core belief text or category."""
    agent = await _get_agent_or_404(agent_id, db)
    data = read_beliefs(agent.name)

    for b in data["core"]:
        if b["id"] == belief_id:
            if body.text is not None:
                b["text"] = body.text.strip()
            if body.category is not None and body.category in BELIEF_CATEGORIES:
                b["category"] = body.category
            write_beliefs(agent.name, data)
            return _format_belief(b, is_core=True)

    raise HTTPException(status_code=404, detail="Core belief not found")


@router.delete("/{agent_id}/beliefs/core/{belief_id}")
async def delete_core_belief(
    agent_id: str,
    belief_id: str,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a core belief."""
    agent = await _get_agent_or_404(agent_id, db)
    data = read_beliefs(agent.name)

    original_len = len(data["core"])
    data["core"] = [b for b in data["core"] if b["id"] != belief_id]
    if len(data["core"]) == original_len:
        raise HTTPException(status_code=404, detail="Core belief not found")

    write_beliefs(agent.name, data)
    return {"message": "Core belief deleted"}


# ── Additional beliefs (user or agent) ──────────────

@router.post("/{agent_id}/beliefs/additional")
async def add_additional_belief(
    agent_id: str,
    body: BeliefCreate,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add an additional belief. Can be created by user or agent."""
    agent = await _get_agent_or_404(agent_id, db)
    data = read_beliefs(agent.name)

    belief = {
        "id": _new_id("add"),
        "text": body.text.strip(),
        "category": body.category if body.category in BELIEF_CATEGORIES else "other",
        "weight": 0.5,
        "created_at": _now_iso(),
        "created_by": "user",
    }
    data["additional"].append(belief)
    write_beliefs(agent.name, data)

    return _format_belief(belief, is_core=False)


@router.put("/{agent_id}/beliefs/additional/{belief_id}")
async def update_additional_belief(
    agent_id: str,
    belief_id: str,
    body: BeliefUpdate,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an additional belief."""
    agent = await _get_agent_or_404(agent_id, db)
    data = read_beliefs(agent.name)

    for b in data["additional"]:
        if b["id"] == belief_id:
            if body.text is not None:
                b["text"] = body.text.strip()
            if body.category is not None and body.category in BELIEF_CATEGORIES:
                b["category"] = body.category
            if body.weight is not None:
                b["weight"] = max(0.0, min(1.0, body.weight))
            write_beliefs(agent.name, data)
            return _format_belief(b, is_core=False)

    raise HTTPException(status_code=404, detail="Additional belief not found")


@router.delete("/{agent_id}/beliefs/additional/{belief_id}")
async def delete_additional_belief(
    agent_id: str,
    belief_id: str,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an additional belief."""
    agent = await _get_agent_or_404(agent_id, db)
    data = read_beliefs(agent.name)

    original_len = len(data["additional"])
    data["additional"] = [b for b in data["additional"] if b["id"] != belief_id]
    if len(data["additional"]) == original_len:
        raise HTTPException(status_code=404, detail="Additional belief not found")

    write_beliefs(agent.name, data)
    return {"message": "Additional belief deleted"}


# ── Reorder ──────────────────────────────────────────

@router.post("/{agent_id}/beliefs/reorder")
async def reorder_beliefs(
    agent_id: str,
    body: dict,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reorder beliefs. Body: {"type": "core"|"additional", "ids": ["id1", "id2", ...]}"""
    agent = await _get_agent_or_404(agent_id, db)
    data = read_beliefs(agent.name)

    belief_type = body.get("type", "additional")
    new_order = body.get("ids", [])

    if belief_type not in ("core", "additional"):
        raise HTTPException(status_code=400, detail="type must be 'core' or 'additional'")

    beliefs_list = data[belief_type]
    by_id = {b["id"]: b for b in beliefs_list}

    reordered = []
    for bid in new_order:
        if bid in by_id:
            reordered.append(by_id.pop(bid))
    # Append any remaining (not in the new_order list)
    reordered.extend(by_id.values())

    data[belief_type] = reordered
    write_beliefs(agent.name, data)

    return {"message": "Reordered"}
