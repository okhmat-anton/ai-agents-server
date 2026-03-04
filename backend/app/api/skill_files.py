"""
Skill Files API — filesystem-based file management within skill directories.
Each skill is a folder under SKILLS_DIR/<skill_name>/ containing code files and a manifest.json.
"""
import json
import os
import shutil
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import get_settings
from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.skill import Skill
from app.schemas.skill import SkillFileInfo, SkillFileContent, SkillFileWrite, SkillFileCreate, SkillFileRename
from app.schemas.common import MessageResponse

router = APIRouter(prefix="/api/skills", tags=["skill-files"])
settings = get_settings()

LANGUAGE_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".sh": "shell",
    ".bash": "shell",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".md": "markdown",
    ".txt": "text",
    ".html": "html",
    ".css": "css",
    ".sql": "sql",
    ".xml": "xml",
    ".env": "shell",
    ".cfg": "ini",
    ".ini": "ini",
    ".dockerfile": "dockerfile",
    ".csv": "text",
}


def _get_language(filename: str) -> str:
    if filename.lower() == "dockerfile":
        return "dockerfile"
    ext = Path(filename).suffix.lower()
    return LANGUAGE_MAP.get(ext, "text")


def _get_skill_dir(skill_name: str) -> Path:
    base = Path(settings.SKILLS_DIR).resolve()
    skill_dir = (base / skill_name).resolve()
    # prevent path traversal
    if not str(skill_dir).startswith(str(base)):
        raise HTTPException(status_code=400, detail="Invalid skill name")
    return skill_dir


def _resolve_path(skill_dir: Path, rel_path: str) -> Path:
    resolved = (skill_dir / rel_path).resolve()
    if not str(resolved).startswith(str(skill_dir)):
        raise HTTPException(status_code=400, detail="Path traversal not allowed")
    return resolved


def _ensure_skills_dir():
    Path(settings.SKILLS_DIR).mkdir(parents=True, exist_ok=True)


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
                "name": entry.name,
                "path": rel_path,
                "is_dir": True,
                "size": 0,
                "language": "",
                "children": children,
            })
        else:
            items.append({
                "name": entry.name,
                "path": rel_path,
                "is_dir": False,
                "size": entry.stat().st_size,
                "language": _get_language(entry.name),
            })
    return items


async def _get_skill_or_404(skill_id: UUID, db: AsyncSession) -> Skill:
    result = await db.execute(select(Skill).where(Skill.id == skill_id))
    skill = result.scalar_one_or_none()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return skill


# ===== Endpoints =====

@router.get("/{skill_id}/files")
async def list_skill_files(
    skill_id: UUID,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all files and folders in a skill directory (tree structure)."""
    skill = await _get_skill_or_404(skill_id, db)
    _ensure_skills_dir()
    skill_dir = _get_skill_dir(skill.name)

    if not skill_dir.exists():
        # create skill dir with default manifest
        skill_dir.mkdir(parents=True, exist_ok=True)
        _write_manifest(skill_dir, skill)

    tree = _scan_dir(skill_dir, skill_dir)
    return tree


@router.get("/{skill_id}/files/read")
async def read_skill_file(
    skill_id: UUID,
    path: str,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SkillFileContent:
    """Read content of a file in the skill directory."""
    skill = await _get_skill_or_404(skill_id, db)
    skill_dir = _get_skill_dir(skill.name)
    file_path = _resolve_path(skill_dir, path)

    if not file_path.exists() or file_path.is_dir():
        raise HTTPException(status_code=404, detail="File not found")

    try:
        content = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Binary file cannot be read as text")

    return SkillFileContent(
        path=path,
        content=content,
        language=_get_language(file_path.name),
    )


@router.put("/{skill_id}/files/write")
async def write_skill_file(
    skill_id: UUID,
    body: SkillFileWrite,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Write/update content of a file in the skill directory."""
    skill = await _get_skill_or_404(skill_id, db)
    if skill.is_system:
        raise HTTPException(status_code=403, detail="Cannot edit system skill files")

    skill_dir = _get_skill_dir(skill.name)
    file_path = _resolve_path(skill_dir, body.path)

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found. Use create endpoint first.")

    file_path.write_text(body.content, encoding="utf-8")

    # if manifest.json was updated, sync back to DB
    if body.path == "manifest.json":
        await _sync_manifest_to_db(skill, skill_dir, db)

    return MessageResponse(message="File saved")


@router.post("/{skill_id}/files/create")
async def create_skill_file(
    skill_id: UUID,
    body: SkillFileCreate,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Create a new file or folder in the skill directory."""
    skill = await _get_skill_or_404(skill_id, db)
    if skill.is_system:
        raise HTTPException(status_code=403, detail="Cannot modify system skill")

    skill_dir = _get_skill_dir(skill.name)
    skill_dir.mkdir(parents=True, exist_ok=True)
    target = _resolve_path(skill_dir, body.path)

    if target.exists():
        raise HTTPException(status_code=409, detail="File or folder already exists")

    if body.is_dir:
        target.mkdir(parents=True)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body.content, encoding="utf-8")

    return MessageResponse(message="Created")


@router.delete("/{skill_id}/files/delete")
async def delete_skill_file(
    skill_id: UUID,
    path: str,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Delete a file or folder from the skill directory."""
    skill = await _get_skill_or_404(skill_id, db)
    if skill.is_system:
        raise HTTPException(status_code=403, detail="Cannot modify system skill")

    skill_dir = _get_skill_dir(skill.name)
    target = _resolve_path(skill_dir, path)

    if not target.exists():
        raise HTTPException(status_code=404, detail="File or folder not found")

    if path == "manifest.json":
        raise HTTPException(status_code=403, detail="Cannot delete manifest.json")

    if target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink()

    return MessageResponse(message="Deleted")


@router.post("/{skill_id}/files/rename")
async def rename_skill_file(
    skill_id: UUID,
    body: SkillFileRename,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Rename/move a file or folder within the skill directory."""
    skill = await _get_skill_or_404(skill_id, db)
    if skill.is_system:
        raise HTTPException(status_code=403, detail="Cannot modify system skill")

    skill_dir = _get_skill_dir(skill.name)
    old = _resolve_path(skill_dir, body.old_path)
    new = _resolve_path(skill_dir, body.new_path)

    if not old.exists():
        raise HTTPException(status_code=404, detail="Source not found")
    if new.exists():
        raise HTTPException(status_code=409, detail="Destination already exists")

    new.parent.mkdir(parents=True, exist_ok=True)
    old.rename(new)

    return MessageResponse(message="Renamed")


# ===== Manifest helpers =====

def _write_manifest(skill_dir: Path, skill: Skill):
    """Write manifest.json from Skill DB record."""
    manifest = {
        "name": skill.name,
        "display_name": skill.display_name,
        "description": skill.description,
        "description_for_agent": skill.description_for_agent,
        "category": skill.category,
        "version": skill.version,
        "entry_point": "main.py",
        "input_schema": skill.input_schema,
        "output_schema": skill.output_schema,
    }
    (skill_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # create default entry point if not exists
    entry = skill_dir / "main.py"
    if not entry.exists():
        entry.write_text(skill.code or "# Entry point\n", encoding="utf-8")


async def _sync_manifest_to_db(skill: Skill, skill_dir: Path, db: AsyncSession):
    """Read manifest.json and sync fields back to DB."""
    manifest_path = skill_dir / "manifest.json"
    if not manifest_path.exists():
        return
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return

    for field in ("display_name", "description", "description_for_agent", "category", "version"):
        if field in manifest:
            setattr(skill, field, manifest[field])

    if "input_schema" in manifest:
        skill.input_schema = manifest["input_schema"]
    if "output_schema" in manifest:
        skill.output_schema = manifest["output_schema"]

    await db.flush()
    await db.refresh(skill)


def init_skill_directory(skill: Skill):
    """Create skill directory and manifest from a newly-created Skill."""
    _ensure_skills_dir()
    skill_dir = _get_skill_dir(skill.name)
    skill_dir.mkdir(parents=True, exist_ok=True)
    _write_manifest(skill_dir, skill)


def delete_skill_directory(skill_name: str):
    """Remove skill directory from filesystem."""
    _ensure_skills_dir()
    skill_dir = _get_skill_dir(skill_name)
    if skill_dir.exists():
        shutil.rmtree(skill_dir)


def duplicate_skill_directory(src_name: str, dst_name: str):
    """Copy an entire skill directory."""
    _ensure_skills_dir()
    src = _get_skill_dir(src_name)
    dst = _get_skill_dir(dst_name)
    if src.exists():
        shutil.copytree(src, dst)
