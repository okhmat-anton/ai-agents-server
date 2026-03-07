"""
System logging service — writes structured logs to the system_logs table.

Usage:
    from app.services.log_service import syslog

    # Inside an async context with a db session:
    await syslog(db, "info", "User logged in", source="auth", metadata={"username": "admin"})

    # Fire-and-forget (creates its own session, safe to call from anywhere):
    await syslog_bg("info", "Server started", source="system")
"""
from __future__ import annotations

import uuid as _uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.log import SystemLog, AgentLog
from app.database import async_session


async def syslog(
    db: AsyncSession,
    level: str,
    message: str,
    *,
    source: str = "system",
    metadata: dict | None = None,
) -> None:
    """Write a log entry using an existing DB session (caller commits)."""
    entry = SystemLog(
        level=level,
        source=source,
        message=message,
        metadata_=metadata,
    )
    db.add(entry)
    try:
        await db.flush()
    except Exception:
        pass  # Don't break the caller if logging fails


async def syslog_bg(
    level: str,
    message: str,
    *,
    source: str = "system",
    metadata: dict | None = None,
) -> None:
    """Fire-and-forget: creates its own session, commits, and closes."""
    try:
        async with async_session() as db:
            entry = SystemLog(
                level=level,
                source=source,
                message=message,
                metadata_=metadata,
            )
            db.add(entry)
            await db.commit()
    except Exception:
        pass  # Logging must never crash the application


# ── Agent logging ─────────────────────────────────────

async def agent_log(
    db: AsyncSession,
    agent_id: _uuid.UUID,
    level: str,
    message: str,
    *,
    metadata: dict | None = None,
) -> None:
    """Write an agent log entry using an existing DB session (caller commits)."""
    entry = AgentLog(
        agent_id=agent_id,
        level=level,
        message=message,
        metadata_=metadata,
    )
    db.add(entry)
    try:
        await db.flush()
    except Exception:
        pass


async def agent_log_bg(
    agent_id: _uuid.UUID | str,
    level: str,
    message: str,
    *,
    metadata: dict | None = None,
) -> None:
    """Fire-and-forget agent log: creates its own session."""
    try:
        aid = agent_id if isinstance(agent_id, _uuid.UUID) else _uuid.UUID(str(agent_id))
        async with async_session() as db:
            entry = AgentLog(
                agent_id=aid,
                level=level,
                message=message,
                metadata_=metadata,
            )
            db.add(entry)
            await db.commit()
    except Exception:
        pass
