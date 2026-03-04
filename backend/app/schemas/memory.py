from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class MemoryCreate(BaseModel):
    title: str
    content: str
    type: str = "fact"
    importance: float = 0.5
    tags: list[str] = []
    category: str = "general"


class MemoryUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    type: str | None = None
    importance: float | None = None
    tags: list[str] | None = None
    category: str | None = None
    is_pinned: bool | None = None


class MemoryResponse(BaseModel):
    id: UUID
    agent_id: UUID
    type: str
    title: str
    content: str
    source: str
    importance: float
    tags: list[str] | None
    category: str
    task_id: UUID | None
    embedding_id: str | None
    access_count: int
    last_accessed: datetime | None
    is_pinned: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MemorySearchRequest(BaseModel):
    query: str
    limit: int = 10
    tags: list[str] | None = None
    category: str | None = None
    importance_min: float | None = None


class MemoryLinkCreate(BaseModel):
    source_id: UUID
    target_id: UUID
    relation_type: str
    strength: float = 0.5
    description: str | None = None


class MemoryLinkResponse(BaseModel):
    id: UUID
    agent_id: UUID
    source_id: UUID
    target_id: UUID
    relation_type: str
    strength: float
    description: str | None
    created_by: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MemoryGraphResponse(BaseModel):
    nodes: list[dict]
    edges: list[dict]


class MemoryStatsResponse(BaseModel):
    total: int = 0
    by_type: dict = {}
    by_category: dict = {}
    top_tags: list[dict] = []
