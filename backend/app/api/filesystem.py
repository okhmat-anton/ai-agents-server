"""
Filesystem API — guarded by the 'filesystem_access_enabled' system setting.
Provides: list, read, write, mkdir, delete, move/rename, info.
"""
import os
import stat
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_mongodb
from app.core.dependencies import get_current_user
from app.api.settings import get_setting_value

router = APIRouter(prefix="/api/fs", tags=["filesystem"])


# ---------- Guard ----------
async def _check_fs_enabled(db: AsyncIOMotorDatabase):
    val = await get_setting_value(db, "filesystem_access_enabled")
    if val != "true":
        raise HTTPException(
            status_code=403,
            detail="Filesystem access is disabled. Enable it in Settings → System.",
        )


def _safe_path(raw: str) -> Path:
    """Resolve and return a Path. Reject obviously bad values."""
    p = Path(raw).expanduser().resolve()
    return p


def _file_info(p: Path) -> dict:
    try:
        st = p.stat()
        return {
            "name": p.name,
            "path": str(p),
            "is_dir": p.is_dir(),
            "is_file": p.is_file(),
            "size": st.st_size,
            "modified": datetime.fromtimestamp(st.st_mtime).isoformat(),
            "created": datetime.fromtimestamp(st.st_ctime).isoformat(),
            "permissions": stat.filemode(st.st_mode),
        }
    except PermissionError:
        return {
            "name": p.name,
            "path": str(p),
            "is_dir": False,
            "is_file": False,
            "size": 0,
            "modified": None,
            "created": None,
            "permissions": "?",
            "error": "Permission denied",
        }


# ---------- Schemas ----------
class WriteRequest(BaseModel):
    path: str
    content: str
    create_dirs: bool = False


class MoveRequest(BaseModel):
    source: str
    destination: str


class MkdirRequest(BaseModel):
    path: str


class DeleteRequest(BaseModel):
    path: str
    recursive: bool = False


# ---------- Endpoints ----------

@router.get("/list")
async def list_directory(
    path: str = Query("/", description="Directory path to list"),
    show_hidden: bool = Query(False),
    _user = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """List files and directories at the given path."""
    await _check_fs_enabled(db)
    p = _safe_path(path)
    if not p.exists():
        raise HTTPException(status_code=404, detail=f"Path not found: {p}")
    if not p.is_dir():
        raise HTTPException(status_code=400, detail=f"Not a directory: {p}")

    items = []
    try:
        for child in sorted(p.iterdir(), key=lambda c: (not c.is_dir(), c.name.lower())):
            if not show_hidden and child.name.startswith("."):
                continue
            items.append(_file_info(child))
    except PermissionError:
        raise HTTPException(status_code=403, detail=f"Permission denied: {p}")

    return {
        "path": str(p),
        "parent": str(p.parent) if p != p.parent else None,
        "items": items,
        "total": len(items),
    }


@router.get("/read")
async def read_file(
    path: str = Query(..., description="File path to read"),
    encoding: str = Query("utf-8"),
    max_size: int = Query(10 * 1024 * 1024, description="Max bytes to read (default 10 MB)"),
    _user = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Read file contents."""
    await _check_fs_enabled(db)
    p = _safe_path(path)
    if not p.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {p}")
    if not p.is_file():
        raise HTTPException(status_code=400, detail=f"Not a file: {p}")
    if p.stat().st_size > max_size:
        raise HTTPException(status_code=400, detail=f"File too large ({p.stat().st_size} bytes). Increase max_size.")

    try:
        content = p.read_text(encoding=encoding)
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Cannot decode file as text. It may be binary.")
    except PermissionError:
        raise HTTPException(status_code=403, detail=f"Permission denied: {p}")

    return {
        "path": str(p),
        "content": content,
        "size": p.stat().st_size,
        "encoding": encoding,
    }


@router.post("/write")
async def write_file(
    body: WriteRequest,
    _user = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Write content to a file."""
    await _check_fs_enabled(db)
    p = _safe_path(body.path)

    if body.create_dirs:
        p.parent.mkdir(parents=True, exist_ok=True)
    elif not p.parent.exists():
        raise HTTPException(status_code=400, detail=f"Parent directory does not exist: {p.parent}")

    try:
        p.write_text(body.content, encoding="utf-8")
    except PermissionError:
        raise HTTPException(status_code=403, detail=f"Permission denied: {p}")

    return {"path": str(p), "size": p.stat().st_size, "message": "File written"}


@router.post("/mkdir")
async def make_directory(
    body: MkdirRequest,
    _user = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Create a directory (with parents)."""
    await _check_fs_enabled(db)
    p = _safe_path(body.path)
    try:
        p.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        raise HTTPException(status_code=403, detail=f"Permission denied: {p}")
    return {"path": str(p), "message": "Directory created"}


@router.post("/delete")
async def delete_path(
    body: DeleteRequest,
    _user = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Delete a file or directory."""
    await _check_fs_enabled(db)
    p = _safe_path(body.path)
    if not p.exists():
        raise HTTPException(status_code=404, detail=f"Path not found: {p}")

    try:
        if p.is_dir():
            if body.recursive:
                shutil.rmtree(p)
            else:
                p.rmdir()  # only empty dirs
        else:
            p.unlink()
    except PermissionError:
        raise HTTPException(status_code=403, detail=f"Permission denied: {p}")
    except OSError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"path": str(p), "message": "Deleted"}


@router.post("/move")
async def move_path(
    body: MoveRequest,
    _user = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Move or rename a file/directory."""
    await _check_fs_enabled(db)
    src = _safe_path(body.source)
    dst = _safe_path(body.destination)
    if not src.exists():
        raise HTTPException(status_code=404, detail=f"Source not found: {src}")

    try:
        shutil.move(str(src), str(dst))
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"source": str(src), "destination": str(dst), "message": "Moved"}


@router.get("/info")
async def path_info(
    path: str = Query(..., description="Path to inspect"),
    _user = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Get detailed info about a path."""
    await _check_fs_enabled(db)
    p = _safe_path(path)
    if not p.exists():
        raise HTTPException(status_code=404, detail=f"Path not found: {p}")
    info = _file_info(p)
    # Add extra details
    if p.is_dir():
        try:
            children = list(p.iterdir())
            info["children_count"] = len(children)
        except PermissionError:
            info["children_count"] = -1
    return info


@router.get("/search")
async def search_files(
    path: str = Query("/", description="Root directory to search in"),
    pattern: str = Query(..., description="Glob pattern, e.g. *.py"),
    max_results: int = Query(200),
    _user = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Search for files matching a glob pattern."""
    await _check_fs_enabled(db)
    p = _safe_path(path)
    if not p.exists() or not p.is_dir():
        raise HTTPException(status_code=400, detail=f"Invalid search root: {p}")

    results = []
    try:
        for match in p.rglob(pattern):
            results.append(_file_info(match))
            if len(results) >= max_results:
                break
    except PermissionError:
        pass

    return {"root": str(p), "pattern": pattern, "results": results, "total": len(results)}


@router.get("/drives")
async def list_drives(
    _user = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """List root drives/mount points."""
    await _check_fs_enabled(db)
    import platform
    system = platform.system()

    if system == "Darwin":
        # macOS: / and /Volumes/*
        drives = [{"path": "/", "name": "Root"}]
        volumes = Path("/Volumes")
        if volumes.exists():
            for v in sorted(volumes.iterdir()):
                drives.append({"path": str(v), "name": v.name})
        return {"system": "macOS", "drives": drives}
    elif system == "Linux":
        drives = [{"path": "/", "name": "Root"}]
        mnt = Path("/mnt")
        if mnt.exists():
            for v in sorted(mnt.iterdir()):
                if v.is_dir():
                    drives.append({"path": str(v), "name": v.name})
        return {"system": "Linux", "drives": drives}
    else:
        # Windows
        import string
        drives = []
        for letter in string.ascii_uppercase:
            dp = Path(f"{letter}:\\")
            if dp.exists():
                drives.append({"path": str(dp), "name": f"{letter}:\\"})
        return {"system": "Windows", "drives": drives}
