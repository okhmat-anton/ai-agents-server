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
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_mongodb
from app.core.dependencies import get_current_user
from app.mongodb.models import MongoUser, MongoAgent, MongoAutonomousRun
from app.mongodb.services import AgentService, AutonomousRunService, ThinkingProtocolService
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


def _run_to_response(run: MongoAutonomousRun, protocol_name: str | None = None) -> AutonomousRunResponse:
    """Convert MongoAutonomousRun to response."""
    return AutonomousRunResponse(
        id=str(run.id),
        agent_id=str(run.agent_id),
        session_id=str(run.session_id) if run.session_id else None,
        mode=run.mode,
        max_cycles=run.max_cycles,
        completed_cycles=run.completed_cycles,
        loop_protocol_id=str(run.loop_protocol_id) if run.loop_protocol_id else None,
        loop_protocol_name=protocol_name,
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
    user: MongoUser = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Start autonomous work for an agent."""
    # Validate agent
    agent_service = AgentService(db)
    agent = await agent_service.get_by_id(str(agent_id))
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
        # Get protocol name if set
        protocol_name = None
        if run.loop_protocol_id:
            protocol_service = ThinkingProtocolService(db)
            protocol = await protocol_service.get_by_id(str(run.loop_protocol_id))
            protocol_name = protocol.name if protocol else None
        return _run_to_response(run, protocol_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/stop", response_model=AutonomousRunResponse)
async def api_stop_autonomous(
    agent_id: UUID,
    user: MongoUser = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Stop the active autonomous run for an agent."""
    agent_service = AgentService(db)
    agent = await agent_service.get_by_id(str(agent_id))
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    active = await get_active_run_for_agent(agent_id)
    if not active:
        raise HTTPException(status_code=404, detail="No active autonomous run")

    try:
        run = await stop_autonomous_run(str(active.id))
        # Get protocol name if set
        protocol_name = None
        if run.loop_protocol_id:
            protocol_service = ThinkingProtocolService(db)
            protocol = await protocol_service.get_by_id(str(run.loop_protocol_id))
            protocol_name = protocol.name if protocol else None
        return _run_to_response(run, protocol_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/status", response_model=Optional[AutonomousRunResponse])
async def api_autonomous_status(
    agent_id: UUID,
    user: MongoUser = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Get the active autonomous run status for an agent."""
    # Get the most recent run (active or last completed)
    run_service = AutonomousRunService(db)
    runs = await run_service.get_all(filter={"agent_id": str(agent_id)}, limit=1)
    # Sort client-side by created_at desc
    runs = sorted(runs, key=lambda r: r.created_at, reverse=True)
    run = runs[0] if runs else None
    
    if not run:
        return None
    
    # Get protocol name if set
    protocol_name = None
    if run.loop_protocol_id:
        protocol_service = ThinkingProtocolService(db)
        protocol = await protocol_service.get_by_id(str(run.loop_protocol_id))
        protocol_name = protocol.name if protocol else None
    
    return _run_to_response(run, protocol_name)


@router.get("/history", response_model=list[AutonomousRunResponse])
async def api_autonomous_history(
    agent_id: UUID,
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    user: MongoUser = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """List all autonomous runs for an agent, newest first."""
    run_service = AutonomousRunService(db)
    protocol_service = ThinkingProtocolService(db)
    
    runs = await run_service.get_all(
        filter={"agent_id": str(agent_id)},
        skip=offset,
        limit=limit
    )
    # Sort client-side by created_at desc
    runs = sorted(runs, key=lambda r: r.created_at, reverse=True)
    
    # Build responses with protocol names
    responses = []
    for run in runs:
        protocol_name = None
        if run.loop_protocol_id:
            protocol = await protocol_service.get_by_id(str(run.loop_protocol_id))
            protocol_name = protocol.name if protocol else None
        responses.append(_run_to_response(run, protocol_name))
    
    return responses


@router.delete("/history")
async def api_clear_autonomous_history(
    agent_id: UUID,
    user: MongoUser = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Delete all completed/stopped/error autonomous runs for an agent (not running ones)."""
    run_service = AutonomousRunService(db)
    
    # Get all non-running runs
    all_runs = await run_service.get_all(filter={"agent_id": str(agent_id)}, limit=10000)
    deleted_count = 0
    for run in all_runs:
        if run.status != "running":
            await run_service.delete(run.id)
            deleted_count += 1
    
    return {"message": f"Deleted {deleted_count} autonomous run(s)"}


@router.get("/{run_id}", response_model=AutonomousRunResponse)
async def api_get_autonomous_run(
    agent_id: UUID,
    run_id: UUID,
    user: MongoUser = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Get a single autonomous run by ID."""
    run_service = AutonomousRunService(db)
    protocol_service = ThinkingProtocolService(db)
    
    run = await run_service.get_by_id(str(run_id))
    if not run or run.agent_id != str(agent_id):
        raise HTTPException(status_code=404, detail="Autonomous run not found")
    
    # Get protocol name if set
    protocol_name = None
    if run.loop_protocol_id:
        protocol = await protocol_service.get_by_id(str(run.loop_protocol_id))
        protocol_name = protocol.name if protocol else None
    
    return _run_to_response(run, protocol_name)
