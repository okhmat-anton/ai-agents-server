"""
Agent Files API — filesystem-based agent configuration and data storage.

Each agent has a folder under AGENTS_DIR/<agent_name>/ containing:
  - agent.json      — agent profile (name, description, system_prompt)
  - settings.json   — generation settings + principles
  - data/           — agent's working files (saved data, downloads, etc.)
"""
import json
import os
import shutil
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import get_settings
from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.agent import Agent
from app.schemas.common import MessageResponse

router = APIRouter(prefix="/api/agents", tags=["agent-files"])
settings = get_settings()

LANGUAGE_MAP = {
    ".py": "python", ".js": "javascript", ".ts": "typescript",
    ".sh": "shell", ".bash": "shell", ".json": "json",
    ".yaml": "yaml", ".yml": "yaml", ".toml": "toml",
    ".md": "markdown", ".txt": "text", ".html": "html",
    ".css": "css", ".sql": "sql", ".xml": "xml",
    ".env": "shell", ".cfg": "ini", ".ini": "ini",
    ".csv": "text", ".log": "text",
}


def _get_language(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    return LANGUAGE_MAP.get(ext, "text")


def _ensure_agents_dir():
    Path(settings.AGENTS_DIR).mkdir(parents=True, exist_ok=True)


def _get_agent_dir(agent_name: str) -> Path:
    base = Path(settings.AGENTS_DIR).resolve()
    agent_dir = (base / agent_name).resolve()
    if not str(agent_dir).startswith(str(base)):
        raise HTTPException(status_code=400, detail="Invalid agent name")
    return agent_dir


def _resolve_path(agent_dir: Path, rel_path: str) -> Path:
    resolved = (agent_dir / rel_path).resolve()
    if not str(resolved).startswith(str(agent_dir)):
        raise HTTPException(status_code=400, detail="Path traversal not allowed")
    return resolved


def _scan_dir(base_dir: Path, current_dir: Path) -> list[dict]:
    """Recursively scan directory and return file tree."""
    items = []
    try:
        entries = sorted(current_dir.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
    except PermissionError:
        return items
    for entry in entries:
        rel_path = str(entry.relative_to(base_dir))
        if entry.is_dir():
            children = _scan_dir(base_dir, entry)
            items.append({
                "name": entry.name, "path": rel_path, "is_dir": True,
                "size": 0, "language": "", "children": children,
            })
        else:
            items.append({
                "name": entry.name, "path": rel_path, "is_dir": False,
                "size": entry.stat().st_size, "language": _get_language(entry.name),
            })
    return items


# ===== JSON config helpers =====

def _write_agent_json(agent_dir: Path, agent: Agent):
    """Write agent.json — profile/description. Preserves mission from existing file."""
    # Read existing mission from file (mission is file-only, not in DB)
    existing = {}
    json_path = agent_dir / "agent.json"
    if json_path.exists():
        try:
            existing = json.loads(json_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    data = {
        "name": agent.name,
        "description": agent.description or "",
        "mission": existing.get("mission", ""),
        "system_prompt": agent.system_prompt or "",
    }
    (agent_dir / "agent.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _write_settings_json(agent_dir: Path, agent: Agent):
    """Write settings.json — generation params."""
    settings_path = agent_dir / "settings.json"
    data = {
        "temperature": agent.temperature,
        "top_p": agent.top_p,
        "top_k": agent.top_k,
        "max_tokens": agent.max_tokens,
        "num_ctx": agent.num_ctx,
        "repeat_penalty": agent.repeat_penalty,
        "num_predict": agent.num_predict,
        "stop": agent.stop or [],
        "num_thread": agent.num_thread,
        "num_gpu": agent.num_gpu,
    }
    settings_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )


async def _sync_agent_json_to_db(agent: Agent, agent_dir: Path, db: AsyncSession):
    """Read agent.json and sync fields back to DB."""
    path = agent_dir / "agent.json"
    if not path.exists():
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return
    for field in ("name", "description", "system_prompt"):
        if field in data:
            setattr(agent, field, data[field])
    await db.flush()
    await db.refresh(agent)


async def _sync_settings_json_to_db(agent: Agent, agent_dir: Path, db: AsyncSession):
    """Read settings.json and sync generation params back to DB."""
    path = agent_dir / "settings.json"
    if not path.exists():
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return
    for field in ("temperature", "top_p", "top_k", "max_tokens", "num_ctx",
                  "repeat_penalty", "num_predict", "stop", "num_thread", "num_gpu"):
        if field in data:
            setattr(agent, field, data[field])
    await db.flush()
    await db.refresh(agent)


def init_agent_directory(agent: Agent):
    """Create agent directory structure from a newly-created Agent."""
    from app.api.agent_beliefs import init_beliefs_file
    _ensure_agents_dir()
    agent_dir = _get_agent_dir(agent.name)
    agent_dir.mkdir(parents=True, exist_ok=True)
    (agent_dir / "data").mkdir(exist_ok=True)
    _write_agent_json(agent_dir, agent)
    _write_settings_json(agent_dir, agent)
    init_beliefs_file(agent.name)


def delete_agent_directory(agent_name: str):
    """Remove agent directory from filesystem."""
    _ensure_agents_dir()
    agent_dir = _get_agent_dir(agent_name)
    if agent_dir.exists():
        shutil.rmtree(agent_dir)


def duplicate_agent_directory(src_name: str, dst_name: str):
    """Copy an entire agent directory."""
    _ensure_agents_dir()
    src = _get_agent_dir(src_name)
    dst = _get_agent_dir(dst_name)
    if src.exists():
        shutil.copytree(src, dst)


def sync_agent_to_filesystem(agent: Agent):
    """Update agent.json and settings.json from DB state (after DB update)."""
    _ensure_agents_dir()
    agent_dir = _get_agent_dir(agent.name)
    if not agent_dir.exists():
        init_agent_directory(agent)
        return
    _write_agent_json(agent_dir, agent)
    _write_settings_json(agent_dir, agent)


def read_agent_config(agent_name: str) -> dict:
    """Read agent.json — the source of truth for agent profile."""
    _ensure_agents_dir()
    agent_dir = _get_agent_dir(agent_name)
    path = agent_dir / "agent.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def read_agent_settings(agent_name: str) -> dict:
    """Read settings.json — the source of truth for generation params & principles."""
    _ensure_agents_dir()
    agent_dir = _get_agent_dir(agent_name)
    path = agent_dir / "settings.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def write_agent_config(agent_name: str, data: dict):
    """Write agent.json from dict."""
    _ensure_agents_dir()
    agent_dir = _get_agent_dir(agent_name)
    agent_dir.mkdir(parents=True, exist_ok=True)
    (agent_dir / "agent.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def write_agent_settings(agent_name: str, data: dict):
    """Write settings.json from dict."""
    _ensure_agents_dir()
    agent_dir = _get_agent_dir(agent_name)
    agent_dir.mkdir(parents=True, exist_ok=True)
    settings_path = agent_dir / "settings.json"
    # Remove legacy principles field if present
    data.pop("principles", None)
    settings_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )


async def _get_agent_or_404(agent_id: UUID, db: AsyncSession) -> Agent:
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


# ===== Endpoints =====

@router.get("/{agent_id}/files")
async def list_agent_files(
    agent_id: UUID,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all files and folders in the agent directory (tree structure)."""
    agent = await _get_agent_or_404(agent_id, db)
    _ensure_agents_dir()
    agent_dir = _get_agent_dir(agent.name)

    if not agent_dir.exists():
        init_agent_directory(agent)

    return _scan_dir(agent_dir, agent_dir)


@router.get("/{agent_id}/files/read")
async def read_agent_file(
    agent_id: UUID,
    path: str,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Read content of a file in the agent directory."""
    agent = await _get_agent_or_404(agent_id, db)
    agent_dir = _get_agent_dir(agent.name)
    file_path = _resolve_path(agent_dir, path)

    if not file_path.exists() or file_path.is_dir():
        raise HTTPException(status_code=404, detail="File not found")

    try:
        content = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Binary file cannot be read as text")

    return {"path": path, "content": content, "language": _get_language(file_path.name)}


@router.put("/{agent_id}/files/write")
async def write_agent_file(
    agent_id: UUID,
    path: str = Query(...),
    content: str = "",
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Write/update content of a file in the agent directory."""
    agent = await _get_agent_or_404(agent_id, db)
    agent_dir = _get_agent_dir(agent.name)
    file_path = _resolve_path(agent_dir, path)

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found. Use create endpoint first.")

    file_path.write_text(content, encoding="utf-8")

    # Sync JSON config files back to DB
    if path == "agent.json":
        await _sync_agent_json_to_db(agent, agent_dir, db)
    elif path == "settings.json":
        await _sync_settings_json_to_db(agent, agent_dir, db)

    return MessageResponse(message="File saved")


@router.put("/{agent_id}/files/write-json")
async def write_agent_file_json(
    agent_id: UUID,
    body: dict,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Write file content via JSON body {path, content}."""
    path = body.get("path", "")
    content = body.get("content", "")
    if not path:
        raise HTTPException(status_code=400, detail="path is required")

    agent = await _get_agent_or_404(agent_id, db)
    agent_dir = _get_agent_dir(agent.name)
    file_path = _resolve_path(agent_dir, path)

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found. Use create endpoint first.")

    file_path.write_text(content, encoding="utf-8")

    if path == "agent.json":
        await _sync_agent_json_to_db(agent, agent_dir, db)
    elif path == "settings.json":
        await _sync_settings_json_to_db(agent, agent_dir, db)

    return MessageResponse(message="File saved")


@router.post("/{agent_id}/files/create")
async def create_agent_file(
    agent_id: UUID,
    body: dict,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Create a new file or folder in the agent directory."""
    agent = await _get_agent_or_404(agent_id, db)
    agent_dir = _get_agent_dir(agent.name)
    agent_dir.mkdir(parents=True, exist_ok=True)

    path = body.get("path", "")
    is_dir = body.get("is_dir", False)
    content = body.get("content", "")

    if not path:
        raise HTTPException(status_code=400, detail="path is required")

    target = _resolve_path(agent_dir, path)
    if target.exists():
        raise HTTPException(status_code=409, detail="File or folder already exists")

    if is_dir:
        target.mkdir(parents=True)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    return MessageResponse(message="Created")


@router.delete("/{agent_id}/files/delete")
async def delete_agent_file(
    agent_id: UUID,
    path: str,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Delete a file or folder from the agent directory."""
    agent = await _get_agent_or_404(agent_id, db)
    agent_dir = _get_agent_dir(agent.name)
    target = _resolve_path(agent_dir, path)

    # Protect config files
    if path in ("agent.json", "settings.json", "beliefs.json"):
        raise HTTPException(status_code=403, detail=f"Cannot delete {path}")
    if path == "data":
        raise HTTPException(status_code=403, detail="Cannot delete data folder")

    if not target.exists():
        raise HTTPException(status_code=404, detail="File or folder not found")

    if target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink()

    return MessageResponse(message="Deleted")


@router.post("/{agent_id}/files/rename")
async def rename_agent_file(
    agent_id: UUID,
    body: dict,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Rename/move a file or folder within the agent directory."""
    agent = await _get_agent_or_404(agent_id, db)
    agent_dir = _get_agent_dir(agent.name)

    old_path = body.get("old_path", "")
    new_path = body.get("new_path", "")
    if not old_path or not new_path:
        raise HTTPException(status_code=400, detail="old_path and new_path required")

    if old_path in ("agent.json", "settings.json", "beliefs.json", "data"):
        raise HTTPException(status_code=403, detail=f"Cannot rename {old_path}")

    old = _resolve_path(agent_dir, old_path)
    new = _resolve_path(agent_dir, new_path)

    if not old.exists():
        raise HTTPException(status_code=404, detail="Source not found")
    if new.exists():
        raise HTTPException(status_code=409, detail="Destination already exists")

    new.parent.mkdir(parents=True, exist_ok=True)
    old.rename(new)

    return MessageResponse(message="Renamed")
