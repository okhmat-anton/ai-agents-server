from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class LogResponse(BaseModel):
    id: UUID
    level: str
    message: str
    metadata_: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SystemLogResponse(LogResponse):
    source: str


class AgentLogResponse(LogResponse):
    agent_id: UUID


class LogQuery(BaseModel):
    level: str | None = None
    source: str | None = None
    search: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    limit: int = 50
    offset: int = 0


class AgentErrorResponse(BaseModel):
    id: UUID
    agent_id: UUID
    error_type: str
    source: str
    message: str
    context: dict | None = None
    resolved: bool
    resolution: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AgentErrorResolve(BaseModel):
    resolution: str = ""
