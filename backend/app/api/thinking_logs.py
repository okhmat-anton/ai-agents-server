"""
Thinking Logs API — view detailed agent reasoning traces.

Endpoints:
  GET  /api/agents/{agent_id}/thinking-logs           — list thinking logs for an agent
  GET  /api/agents/{agent_id}/thinking-logs/{log_id}  — get single thinking log with all steps
  GET  /api/chat/sessions/{session_id}/thinking-logs   — list thinking logs for a chat session
  DELETE /api/agents/{agent_id}/thinking-logs          — clear all thinking logs for an agent
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.agent import Agent
from app.models.thinking_log import ThinkingLog, ThinkingStep
from app.schemas.thinking_log import ThinkingLogResponse, ThinkingLogSummaryResponse

# --- Agent-scoped routes ---
agent_thinking_router = APIRouter(prefix="/api/agents/{agent_id}/thinking-logs", tags=["thinking-logs"])


@agent_thinking_router.get("", response_model=list[ThinkingLogSummaryResponse])
async def list_agent_thinking_logs(
    agent_id: UUID,
    status: str | None = Query(None, description="Filter by status: started, completed, error"),
    limit: int = Query(50, le=500),
    offset: int = Query(0, ge=0),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List thinking log summaries for an agent, newest first."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Agent not found")

    q = select(ThinkingLog).where(ThinkingLog.agent_id == agent_id)
    if status:
        q = q.where(ThinkingLog.status == status)
    q = q.order_by(ThinkingLog.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(q)
    logs = result.scalars().all()

    # Build summaries with steps_count
    summaries = []
    for log in logs:
        summary = ThinkingLogSummaryResponse.model_validate(log)
        # Count steps via the loaded relationship or a count
        summary.steps_count = len(log.steps) if log.steps else 0
        summaries.append(summary)
    return summaries


@agent_thinking_router.get("/{log_id}", response_model=ThinkingLogResponse)
async def get_thinking_log(
    agent_id: UUID,
    log_id: UUID,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single thinking log with all steps."""
    result = await db.execute(
        select(ThinkingLog)
        .options(selectinload(ThinkingLog.steps))
        .where(ThinkingLog.id == log_id, ThinkingLog.agent_id == agent_id)
    )
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=404, detail="Thinking log not found")
    return log


@agent_thinking_router.delete("")
async def clear_agent_thinking_logs(
    agent_id: UUID,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Clear all thinking logs for an agent."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Agent not found")

    await db.execute(delete(ThinkingLog).where(ThinkingLog.agent_id == agent_id))
    await db.flush()
    return {"message": "Thinking logs cleared"}


# --- Session-scoped routes ---
session_thinking_router = APIRouter(prefix="/api/chat/sessions/{session_id}/thinking-logs", tags=["thinking-logs"])


@session_thinking_router.get("", response_model=list[ThinkingLogSummaryResponse])
async def list_session_thinking_logs(
    session_id: UUID,
    limit: int = Query(50, le=500),
    offset: int = Query(0, ge=0),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List thinking logs for a chat session, ordered by time."""
    q = (
        select(ThinkingLog)
        .where(ThinkingLog.session_id == session_id)
        .order_by(ThinkingLog.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(q)
    logs = result.scalars().all()

    summaries = []
    for log in logs:
        summary = ThinkingLogSummaryResponse.model_validate(log)
        summary.steps_count = len(log.steps) if log.steps else 0
        summaries.append(summary)
    return summaries
