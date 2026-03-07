"""
Autonomous Run API — start, stop, monitor autonomous agent work.

Endpoints:
  POST   /api/agents/{agent_id}/autonomous/start    — start autonomous work
  POST   /api/agents/{agent_id}/autonomous/stop     — stop current autonomous run
  GET    /api/agents/{agent_id}/autonomous/status    — get active run status
  GET    /api/agents/{agent_id}/autonomous/history   — list past runs
  GET    /api/agents/{agent_id}/autonomous/{run_id}  — get single run details
"""
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.agent import Agent
from app.models.autonomous_run import AutonomousRun
from app.services.autonomous_runner import (
    start_autonomous_run,
    stop_autonomous_run,
    get_active_run_for_agent,
    active_runs,
)

router = APIRouter(prefix="/api/agents/{agent_id}/autonomous", tags=["autonomous"])


# ── Schemas ──────────────────────────────────────────────

class StartAutonomousRequest(BaseModel):
    mode: str = "continuous"  # continuous | cycles
    max_cycles: Optional[int] = None
    loop_protocol_id: Optional[str] = None


class AutonomousRunResponse(BaseModel):
    id: str
    agent_id: str
    session_id: Optional[str] = None
    mode: str
    max_cycles: Optional[int] = None
    completed_cycles: int = 0
    loop_protocol_id: Optional[str] = None
    loop_protocol_name: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    cycle_state: Optional[dict] = None
    total_duration_ms: int = 0
    total_tokens: int = 0
    total_llm_calls: int = 0
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    is_active: bool = False

    model_config = {"from_attributes": True}


def _run_to_response(run: AutonomousRun) -> AutonomousRunResponse:
    """Convert AutonomousRun to response."""
    return AutonomousRunResponse(
        id=str(run.id),
        agent_id=str(run.agent_id),
        session_id=str(run.session_id) if run.session_id else None,
        mode=run.mode,
        max_cycles=run.max_cycles,
        completed_cycles=run.completed_cycles,
        loop_protocol_id=str(run.loop_protocol_id) if run.loop_protocol_id else None,
        loop_protocol_name=run.loop_protocol.name if run.loop_protocol else None,
        status=run.status,
        error_message=run.error_message,
        cycle_state=run.cycle_state,
        total_duration_ms=run.total_duration_ms or 0,
        total_tokens=run.total_tokens or 0,
        total_llm_calls=run.total_llm_calls or 0,
        created_at=run.created_at.isoformat() if run.created_at else "",
        started_at=run.started_at.isoformat() if run.started_at else None,
        completed_at=run.completed_at.isoformat() if run.completed_at else None,
        is_active=str(run.id) in active_runs,
    )


# ── Endpoints ────────────────────────────────────────────

@router.post("/start", response_model=AutonomousRunResponse)
async def api_start_autonomous(
    agent_id: UUID,
    body: StartAutonomousRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Start autonomous work for an agent."""
    # Validate agent
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    if agent.status == "running":
        raise HTTPException(status_code=409, detail="Agent is already running")

    # Check for existing active run
    existing = await get_active_run_for_agent(agent_id)
    if existing:
        raise HTTPException(status_code=409, detail="Agent already has an active autonomous run")

    # Validate mode
    if body.mode not in ("continuous", "cycles"):
        raise HTTPException(status_code=400, detail="Mode must be 'continuous' or 'cycles'")

    if body.mode == "cycles" and (not body.max_cycles or body.max_cycles < 1):
        raise HTTPException(status_code=400, detail="max_cycles must be >= 1 for cycles mode")

    try:
        run = await start_autonomous_run(
            agent_id=agent_id,
            mode=body.mode,
            max_cycles=body.max_cycles,
            loop_protocol_id=UUID(body.loop_protocol_id) if body.loop_protocol_id else None,
            user_id=user.id,
        )
        return _run_to_response(run)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/stop", response_model=AutonomousRunResponse)
async def api_stop_autonomous(
    agent_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Stop the active autonomous run for an agent."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    active = await get_active_run_for_agent(agent_id)
    if not active:
        raise HTTPException(status_code=404, detail="No active autonomous run")

    try:
        run = await stop_autonomous_run(str(active.id))
        return _run_to_response(run)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/status", response_model=Optional[AutonomousRunResponse])
async def api_autonomous_status(
    agent_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the active autonomous run status for an agent."""
    # Get the most recent run (active or last completed)
    result = await db.execute(
        select(AutonomousRun).where(
            AutonomousRun.agent_id == agent_id,
        ).order_by(AutonomousRun.created_at.desc()).limit(1)
    )
    run = result.scalar_one_or_none()
    if not run:
        return None
    return _run_to_response(run)


@router.get("/history", response_model=list[AutonomousRunResponse])
async def api_autonomous_history(
    agent_id: UUID,
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all autonomous runs for an agent, newest first."""
    result = await db.execute(
        select(AutonomousRun).where(
            AutonomousRun.agent_id == agent_id,
        ).order_by(AutonomousRun.created_at.desc()).limit(limit).offset(offset)
    )
    runs = result.scalars().all()
    return [_run_to_response(r) for r in runs]


@router.delete("/history")
async def api_clear_autonomous_history(
    agent_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete all completed/stopped/error autonomous runs for an agent (not running ones)."""
    from sqlalchemy import delete
    result = await db.execute(
        delete(AutonomousRun).where(
            AutonomousRun.agent_id == agent_id,
            AutonomousRun.status.notin_(["running"]),
        )
    )
    await db.commit()
    return {"message": f"Deleted {result.rowcount} autonomous run(s)"}


@router.get("/{run_id}", response_model=AutonomousRunResponse)
async def api_get_autonomous_run(
    agent_id: UUID,
    run_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single autonomous run by ID."""
    result = await db.execute(
        select(AutonomousRun).where(
            AutonomousRun.id == run_id,
            AutonomousRun.agent_id == agent_id,
        )
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Autonomous run not found")
    return _run_to_response(run)
