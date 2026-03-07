from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class TaskCreate(BaseModel):
    title: str
    description: str = ""
    type: str = "one_time"
    priority: str = "normal"
    schedule: str | None = None
    max_retries: int = 3
    timeout: int = 300


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    type: str | None = None
    priority: str | None = None
    schedule: str | None = None
    max_retries: int | None = None
    timeout: int | None = None


class TaskResponse(BaseModel):
    id: UUID
    agent_id: UUID | None
    agent_name: str | None = None
    title: str
    description: str
    type: str
    status: str
    priority: str
    schedule: str | None
    next_run_at: datetime | None
    max_retries: int
    retry_count: int
    timeout: int
    result: dict | None
    error: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
