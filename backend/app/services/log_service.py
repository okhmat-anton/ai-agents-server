"""
System logging service — writes structured logs to JSON files.

Usage:
    from app.services.log_service import syslog

    # Async log
    await syslog("info", "User logged in", source="auth", metadata={"username": "admin"})

    # Fire-and-forget
    await syslog_bg("info", "Server started", source="system")
"""
from __future__ import annotations

import uuid as _uuid
import json
import aiofiles
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

# Log directories — resolve relative to project root (4 levels up from this file)
_PROJECT_ROOT = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))).resolve()
LOG_DIR = _PROJECT_ROOT / "data" / "logs"
SYSTEM_LOG_FILE = LOG_DIR / "system.jsonl"
AGENT_LOG_DIR = LOG_DIR / "agents"

# Ensure log directories exist
LOG_DIR.mkdir(parents=True, exist_ok=True)
AGENT_LOG_DIR.mkdir(parents=True, exist_ok=True)


async def syslog(
    level_or_db: Any,
    message_or_level: str = None,
    message: str = None,
    source: str = "system",
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Write a system log entry to file.
    
    Supports both signatures:
      - syslog("info", "message", source="auth")  # new
      - syslog(db, "info", "message", source="auth")  # legacy
    """
    # Determine which signature was used
    if message is not None:
        # Old signature: syslog(db, level, message, ...)
        actual_level = message_or_level
        actual_message = message
    else:
        # New signature: syslog(level, message, ...)
        actual_level = level_or_db
        actual_message = message_or_level
    
    try:
        entry = {
            "id": str(_uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "level": actual_level,
            "source": source,
            "message": actual_message,
            "metadata": metadata or {},
        }
        async with aiofiles.open(SYSTEM_LOG_FILE, mode="a") as f:
            await f.write(json.dumps(entry) + "\n")
    except Exception:
        pass  # Don't break the caller if logging fails


async def syslog_bg(
    level: str,
    message: str,
    *,
    source: str = "system",
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Fire-and-forget system log (same as syslog for file-based)."""
    await syslog(level, message, source=source, metadata=metadata)


# ── Agent logging ─────────────────────────────────────

async def agent_log(
    agent_id: _uuid.UUID,
    level: str,
    message: str,
    *,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Write an agent log entry to file."""
    try:
        agent_log_file = AGENT_LOG_DIR / f"{agent_id}.jsonl"
        entry = {
            "id": str(_uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "agent_id": str(agent_id),
            "level": level,
            "message": message,
            "metadata": metadata or {},
        }
        async with aiofiles.open(agent_log_file, mode="a") as f:
            await f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


async def agent_log_bg(
    agent_id: _uuid.UUID | str,
    level: str,
    message: str,
    *,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Fire-and-forget agent log."""
    aid = agent_id if isinstance(agent_id, _uuid.UUID) else _uuid.UUID(str(agent_id))
    await agent_log(aid, level, message, metadata=metadata)


# ── Reading / clearing logs ───────────────────────────

async def read_system_logs(limit: int = 500) -> list[dict]:
    """Read system log entries from file. Returns most recent first."""
    if not SYSTEM_LOG_FILE.exists():
        return []
    try:
        async with aiofiles.open(SYSTEM_LOG_FILE, mode="r") as f:
            content = await f.read()
        lines = content.strip().split("\n") if content.strip() else []
        logs = []
        for line in lines:
            try:
                logs.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        # Return newest first
        logs.reverse()
        if limit > 0:
            return logs[:limit]
        return logs
    except Exception:
        return []


async def clear_old_system_logs(days: int = 30) -> int:
    """Remove system log entries older than N days. Returns count of removed entries."""
    if not SYSTEM_LOG_FILE.exists():
        return 0
    from datetime import timedelta
    cutoff = datetime.utcnow() - timedelta(days=days)
    cutoff_str = cutoff.isoformat()

    try:
        async with aiofiles.open(SYSTEM_LOG_FILE, mode="r") as f:
            content = await f.read()
        lines = content.strip().split("\n") if content.strip() else []

        kept = []
        removed = 0
        for line in lines:
            try:
                entry = json.loads(line)
                ts = entry.get("timestamp", "")
                if ts < cutoff_str:
                    removed += 1
                else:
                    kept.append(line)
            except json.JSONDecodeError:
                kept.append(line)

        async with aiofiles.open(SYSTEM_LOG_FILE, mode="w") as f:
            await f.write("\n".join(kept) + "\n" if kept else "")

        return removed
    except Exception:
        return 0