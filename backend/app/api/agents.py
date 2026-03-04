from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.agent import Agent
from app.models.agent_model import AgentModel
from app.models.task import Task
from app.models.log import AgentLog
from app.models.memory import Memory
from app.models.skill import AgentSkill
from app.schemas.agent import AgentCreate, AgentUpdate, AgentResponse, AgentStatsResponse, AgentModelResponse
from app.schemas.common import MessageResponse

router = APIRouter(prefix="/api/agents", tags=["agents"])


async def _load_agent(db: AsyncSession, agent_id) -> Agent | None:
    """Load agent with agent_models + nested model_config_rel eagerly."""
    result = await db.execute(
        select(Agent)
        .where(Agent.id == agent_id)
        .options(
            selectinload(Agent.agent_models).selectinload(AgentModel.model_config_rel)
        )
    )
    return result.scalar_one_or_none()


def _build_agent_response(agent: Agent) -> dict:
    """Build response dict with resolved model names from agent_models."""
    data = {c.key: getattr(agent, c.key) for c in agent.__table__.columns}
    agent_models_out = []
    for am in (agent.agent_models or []):
        mcr = am.model_config_rel
        agent_models_out.append(AgentModelResponse(
            id=am.id,
            model_config_id=am.model_config_id,
            model_name=mcr.model_id if mcr else None,
            model_display_name=mcr.name if mcr else None,
            task_type=am.task_type,
            tags=am.tags or [],
            priority=am.priority,
            created_at=am.created_at,
        ))
    data["agent_models"] = agent_models_out
    return data


@router.get("", response_model=list[AgentResponse])
async def list_agents(
    status: str | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(Agent).options(
        selectinload(Agent.agent_models).selectinload(AgentModel.model_config_rel)
    )
    if status:
        q = q.where(Agent.status == status)
    q = q.order_by(Agent.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(q)
    agents = result.scalars().all()
    return [_build_agent_response(a) for a in agents]


@router.post("", response_model=AgentResponse, status_code=201)
async def create_agent(
    body: AgentCreate,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    agent_data = body.model_dump(exclude={"models"})
    agent = Agent(**agent_data)
    db.add(agent)
    await db.flush()

    # Create agent_model entries
    for entry in body.models:
        am = AgentModel(
            agent_id=agent.id,
            model_config_id=entry.model_config_id,
            task_type=entry.task_type,
            tags=entry.tags,
            priority=entry.priority,
        )
        db.add(am)
    await db.flush()
    agent = await _load_agent(db, agent.id)
    return _build_agent_response(agent)


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: UUID,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    agent = await _load_agent(db, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return _build_agent_response(agent)


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: UUID,
    body: AgentUpdate,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    update_data = body.model_dump(exclude_unset=True, exclude={"models"})
    for key, value in update_data.items():
        setattr(agent, key, value)

    # If models list is provided, replace all agent_model entries
    if body.models is not None:
        await db.execute(delete(AgentModel).where(AgentModel.agent_id == agent_id))
        for entry in body.models:
            am = AgentModel(
                agent_id=agent.id,
                model_config_id=entry.model_config_id,
                task_type=entry.task_type,
                tags=entry.tags,
                priority=entry.priority,
            )
            db.add(am)

    await db.flush()
    agent = await _load_agent(db, agent.id)
    return _build_agent_response(agent)


@router.delete("/{agent_id}", response_model=MessageResponse)
async def delete_agent(
    agent_id: UUID,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    await db.delete(agent)
    return MessageResponse(message="Agent deleted")


@router.post("/{agent_id}/start", response_model=AgentResponse)
async def start_agent(
    agent_id: UUID,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent.status = "running"
    from datetime import datetime, timezone
    agent.last_run_at = datetime.now(timezone.utc)
    await db.flush()
    agent = await _load_agent(db, agent_id)
    return _build_agent_response(agent)


@router.post("/{agent_id}/stop", response_model=AgentResponse)
async def stop_agent(
    agent_id: UUID,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent.status = "stopped"
    await db.flush()
    agent = await _load_agent(db, agent_id)
    return _build_agent_response(agent)


@router.post("/{agent_id}/pause", response_model=AgentResponse)
async def pause_agent(
    agent_id: UUID,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent.status = "paused"
    await db.flush()
    agent = await _load_agent(db, agent_id)
    return _build_agent_response(agent)


@router.post("/{agent_id}/resume", response_model=AgentResponse)
async def resume_agent(
    agent_id: UUID,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent.status = "running"
    await db.flush()
    agent = await _load_agent(db, agent_id)
    return _build_agent_response(agent)


@router.post("/{agent_id}/duplicate", response_model=AgentResponse, status_code=201)
async def duplicate_agent(
    agent_id: UUID,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    agent = await _load_agent(db, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    new_agent = Agent(
        name=f"{agent.name} (copy)",
        description=agent.description,
        system_prompt=agent.system_prompt,
        temperature=agent.temperature,
        top_p=agent.top_p,
        top_k=agent.top_k,
        max_tokens=agent.max_tokens,
        num_ctx=agent.num_ctx,
        repeat_penalty=agent.repeat_penalty,
        num_predict=agent.num_predict,
        stop=agent.stop,
        num_thread=agent.num_thread,
        num_gpu=agent.num_gpu,
    )
    db.add(new_agent)
    await db.flush()

    # Duplicate agent_models
    for am in agent.agent_models:
        new_am = AgentModel(
            agent_id=new_agent.id,
            model_config_id=am.model_config_id,
            task_type=am.task_type,
            tags=am.tags,
            priority=am.priority,
        )
        db.add(new_am)
    await db.flush()
    new_agent = await _load_agent(db, new_agent.id)
    return _build_agent_response(new_agent)


@router.get("/{agent_id}/stats", response_model=AgentStatsResponse)
async def agent_stats(
    agent_id: UUID,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify agent exists
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Agent not found")

    total_tasks = (await db.execute(select(func.count(Task.id)).where(Task.agent_id == agent_id))).scalar() or 0
    completed = (await db.execute(select(func.count(Task.id)).where(Task.agent_id == agent_id, Task.status == "completed"))).scalar() or 0
    failed = (await db.execute(select(func.count(Task.id)).where(Task.agent_id == agent_id, Task.status == "failed"))).scalar() or 0
    logs = (await db.execute(select(func.count(AgentLog.id)).where(AgentLog.agent_id == agent_id))).scalar() or 0
    memories = (await db.execute(select(func.count(Memory.id)).where(Memory.agent_id == agent_id))).scalar() or 0
    skills = (await db.execute(select(func.count(AgentSkill.skill_id)).where(AgentSkill.agent_id == agent_id))).scalar() or 0

    return AgentStatsResponse(
        total_tasks=total_tasks,
        completed_tasks=completed,
        failed_tasks=failed,
        total_logs=logs,
        total_memories=memories,
        total_skills=skills,
    )
