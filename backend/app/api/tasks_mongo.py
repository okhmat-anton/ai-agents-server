"""
Tasks API - MongoDB version.
Migrated from PostgreSQL to MongoDB for better JSON document storage.
"""
from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_mongodb
from app.core.dependencies import get_current_user
from app.schemas.task import TaskCreate, TaskUpdate, TaskResponse
from app.schemas.common import MessageResponse
from app.mongodb.task_service import (
    create_task,
    get_task_by_id,
    list_tasks,
    update_task,
    delete_task,
)
from app.mongodb.models import MongoTask
from app.mongodb.services import AgentService

router = APIRouter(tags=["tasks"])

# ------- Common Tasks -------
common_router = APIRouter(prefix="/api/tasks")


@common_router.get("", response_model=list[TaskResponse])
async def list_all_tasks(
    status: str | None = Query(None),
    priority: str | None = Query(None),
    type: str | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    _user = Depends(get_current_user),
):
    """List all tasks with optional filters."""
    tasks = await list_tasks(
        agent_id=None,
        status=status,
        type=type,
        limit=limit,
        skip=offset
    )
    
    # Filter by priority if specified (MongoDB query builder doesn't support yet)
    if priority:
        tasks = [t for t in tasks if t.priority == priority]
    
    return [TaskResponse(**t.model_dump()) for t in tasks]


@common_router.post("", response_model=TaskResponse, status_code=201)
async def create_new_task(
    body: TaskCreate,
    _user = Depends(get_current_user),
):
    """Create a new task."""
    task = MongoTask(**body.model_dump(), agent_id=None)
    created_task = await create_task(task)
    return TaskResponse(**created_task.model_dump())


@common_router.get("/{task_id}", response_model=TaskResponse)
async def get_task_details(
    task_id: UUID,
    _user = Depends(get_current_user),
):
    """Get task by ID."""
    task = await get_task_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse(**task.model_dump())


@common_router.put("/{task_id}", response_model=TaskResponse)
async def update_task_details(
    task_id: UUID,
    body: TaskUpdate,
    _user = Depends(get_current_user),
):
    """Update task."""
    updates = body.model_dump(exclude_unset=True)
    task = await update_task(task_id, updates)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse(**task.model_dump())


@common_router.delete("/{task_id}", response_model=MessageResponse)
async def remove_task(
    task_id: UUID,
    _user = Depends(get_current_user),
):
    """Delete task."""
    deleted = await delete_task(task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")
    return MessageResponse(message="Task deleted")


@common_router.post("/{task_id}/run", response_model=TaskResponse)
async def run_task_now(
    task_id: UUID,
    _user = Depends(get_current_user),
):
    """Run task immediately."""
    task = await update_task(task_id, {
        "status": "running",
        "started_at": datetime.now(timezone.utc)
    })
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse(**task.model_dump())


@common_router.post("/{task_id}/cancel", response_model=TaskResponse)
async def cancel_task_execution(
    task_id: UUID,
    _user = Depends(get_current_user),
):
    """Cancel task execution."""
    task = await update_task(task_id, {"status": "cancelled"})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse(**task.model_dump())


# ------- Agent Tasks -------
agent_task_router = APIRouter(prefix="/api/agents/{agent_id}/tasks")


async def _get_agent(agent_id: UUID, db: AsyncIOMotorDatabase):
    """Helper to verify agent exists."""
    agent = await AgentService(db).get_by_id(str(agent_id))
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@agent_task_router.get("", response_model=list[TaskResponse])
async def list_agent_tasks(
    agent_id: UUID,
    status: str | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    _user = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """List tasks for specific agent."""
    await _get_agent(agent_id, db)
    tasks = await list_tasks(
        agent_id=agent_id,
        status=status,
        limit=limit,
        skip=offset
    )
    return [TaskResponse(**t.model_dump()) for t in tasks]


@agent_task_router.post("", response_model=TaskResponse, status_code=201)
async def create_agent_task(
    agent_id: UUID,
    body: TaskCreate,
    _user = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Create task for agent."""
    await _get_agent(agent_id, db)
    task = MongoTask(**body.model_dump(), agent_id=str(agent_id))
    created_task = await create_task(task)
    return TaskResponse(**created_task.model_dump())


@agent_task_router.get("/{task_id}", response_model=TaskResponse)
async def get_agent_task_details(
    agent_id: UUID,
    task_id: UUID,
    _user = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Get specific task for agent."""
    await _get_agent(agent_id, db)
    task = await get_task_by_id(task_id)
    if not task or str(task.agent_id) != str(agent_id):
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse(**task.model_dump())


@agent_task_router.put("/{task_id}", response_model=TaskResponse)
async def update_agent_task_details(
    agent_id: UUID,
    task_id: UUID,
    body: TaskUpdate,
    _user = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Update agent task."""
    await _get_agent(agent_id, db)
    # Verify task belongs to agent
    existing_task = await get_task_by_id(task_id)
    if not existing_task or existing_str(task.agent_id) != str(agent_id):
        raise HTTPException(status_code=404, detail="Task not found")
    
    updates = body.model_dump(exclude_unset=True)
    task = await update_task(task_id, updates)
    return TaskResponse(**task.model_dump())


@agent_task_router.delete("/{task_id}", response_model=MessageResponse)
async def remove_agent_task(
    agent_id: UUID,
    task_id: UUID,
    _user = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Delete agent task."""
    await _get_agent(agent_id, db)
    # Verify task belongs to agent
    existing_task = await get_task_by_id(task_id)
    if not existing_task or existing_str(task.agent_id) != str(agent_id):
        raise HTTPException(status_code=404, detail="Task not found")
    
    await delete_task(task_id)
    return MessageResponse(message="Task deleted")


@agent_task_router.post("/{task_id}/run", response_model=TaskResponse)
async def run_agent_task_now(
    agent_id: UUID,
    task_id: UUID,
    _user = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Run agent task immediately."""
    await _get_agent(agent_id, db)
    # Verify task belongs to agent
    existing_task = await get_task_by_id(task_id)
    if not existing_task or existing_str(task.agent_id) != str(agent_id):
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = await update_task(task_id, {
        "status": "running",
        "started_at": datetime.now(timezone.utc)
    })
    return TaskResponse(**task.model_dump())


@agent_task_router.post("/{task_id}/cancel", response_model=TaskResponse)
async def cancel_agent_task_execution(
    agent_id: UUID,
    task_id: UUID,
    _user = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Cancel agent task execution."""
    await _get_agent(agent_id, db)
    # Verify task belongs to agent
    existing_task = await get_task_by_id(task_id)
    if not existing_task or existing_str(task.agent_id) != str(agent_id):
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = await update_task(task_id, {"status": "cancelled"})
    return TaskResponse(**task.model_dump())
