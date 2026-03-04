"""
Terminal API — execute shell commands on the host.
Guarded by the 'system_access_enabled' system setting.
"""
import asyncio
import os
import uuid
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.api.settings import get_setting_value

router = APIRouter(prefix="/api/terminal", tags=["terminal"])


# ---------- Guard ----------
async def _check_system_access(db: AsyncSession):
    val = await get_setting_value(db, "system_access_enabled")
    if val != "true":
        raise HTTPException(
            status_code=403,
            detail="System access is disabled. Enable it in Settings → System.",
        )


# ---------- Schemas ----------
class ExecuteRequest(BaseModel):
    command: str
    cwd: Optional[str] = None
    timeout: int = 30  # seconds
    env: Optional[dict[str, str]] = None


class ExecuteResponse(BaseModel):
    id: str
    command: str
    stdout: str
    stderr: str
    exit_code: int | None
    duration_ms: int
    timed_out: bool = False


# ---------- Session storage for long-running commands ----------
_sessions: dict[str, dict] = {}


# ---------- Endpoints ----------

@router.post("/execute", response_model=ExecuteResponse)
async def execute_command(
    body: ExecuteRequest,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Execute a shell command and return its output."""
    await _check_system_access(db)

    cmd_id = str(uuid.uuid4())[:8]
    cwd = body.cwd or os.path.expanduser("~")
    timeout = min(body.timeout, 300)  # hard cap at 5 minutes

    # Build env
    env = os.environ.copy()
    if body.env:
        env.update(body.env)

    start = time.monotonic()
    timed_out = False

    try:
        proc = await asyncio.create_subprocess_shell(
            body.command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
            env=env,
        )
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
        except asyncio.TimeoutError:
            proc.kill()
            stdout_bytes, stderr_bytes = await proc.communicate()
            timed_out = True

    except FileNotFoundError:
        raise HTTPException(status_code=400, detail=f"Working directory not found: {cwd}")
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    elapsed = int((time.monotonic() - start) * 1000)

    # Limit output size to 1MB to prevent memory issues
    max_output = 1024 * 1024
    stdout = stdout_bytes.decode("utf-8", errors="replace")[:max_output]
    stderr = stderr_bytes.decode("utf-8", errors="replace")[:max_output]

    return ExecuteResponse(
        id=cmd_id,
        command=body.command,
        stdout=stdout,
        stderr=stderr,
        exit_code=proc.returncode,
        duration_ms=elapsed,
        timed_out=timed_out,
    )


@router.post("/execute-stream")
async def execute_command_stream(
    body: ExecuteRequest,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Execute a command and stream output via SSE."""
    await _check_system_access(db)

    cwd = body.cwd or os.path.expanduser("~")
    timeout = min(body.timeout, 300)

    env = os.environ.copy()
    if body.env:
        env.update(body.env)

    async def event_generator():
        try:
            proc = await asyncio.create_subprocess_shell(
                body.command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=env,
            )

            start = time.monotonic()

            async def read_stream(stream, prefix):
                while True:
                    if time.monotonic() - start > timeout:
                        break
                    line = await asyncio.wait_for(stream.readline(), timeout=1.0)
                    if not line:
                        break
                    text = line.decode("utf-8", errors="replace").rstrip("\n")
                    yield f"data: {prefix}:{text}\n\n"

            async for chunk in read_stream(proc.stdout, "stdout"):
                yield chunk
            async for chunk in read_stream(proc.stderr, "stderr"):
                yield chunk

            await proc.wait()
            yield f"data: exit:{proc.returncode}\n\n"

        except asyncio.TimeoutError:
            yield "data: error:Command timed out\n\n"
        except Exception as e:
            yield f"data: error:{str(e)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/completions")
async def get_completions(
    text: str = Query(..., description="Partial command text"),
    cwd: str = Query(None),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get basic command completions (programs in PATH, files in cwd)."""
    await _check_system_access(db)

    working_dir = cwd or os.path.expanduser("~")
    completions = []

    # File/dir completions in cwd
    parts = text.rsplit(" ", 1)
    prefix = parts[-1] if len(parts) > 1 else text

    from pathlib import Path
    try:
        base = Path(working_dir)
        if "/" in prefix:
            base = Path(prefix).parent
            if not base.is_absolute():
                base = Path(working_dir) / base
            prefix = Path(prefix).name

        for child in sorted(base.iterdir()):
            if child.name.startswith(prefix) or not prefix:
                completions.append({
                    "text": child.name + ("/" if child.is_dir() else ""),
                    "type": "dir" if child.is_dir() else "file",
                })
            if len(completions) >= 50:
                break
    except (PermissionError, FileNotFoundError):
        pass

    return {"completions": completions}


@router.get("/history")
async def get_shell_history(
    limit: int = Query(50, le=200),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Read recent shell history from the host."""
    await _check_system_access(db)

    from pathlib import Path
    history_files = [
        Path.home() / ".zsh_history",
        Path.home() / ".bash_history",
    ]

    lines = []
    for hf in history_files:
        if hf.exists():
            try:
                raw = hf.read_bytes()
                text = raw.decode("utf-8", errors="replace")
                all_lines = text.strip().split("\n")
                # zsh history format: : timestamp:0;command
                parsed = []
                for l in all_lines:
                    if l.startswith(": ") and ";" in l:
                        parsed.append(l.split(";", 1)[1])
                    else:
                        parsed.append(l)
                lines = parsed[-limit:]
                break
            except PermissionError:
                continue

    return {"history": lines, "count": len(lines)}
