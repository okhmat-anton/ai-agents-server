from pydantic import BaseModel


class PaginatedResponse(BaseModel):
    items: list
    total: int
    limit: int
    offset: int


class MessageResponse(BaseModel):
    message: str


class HealthResponse(BaseModel):
    status: str
    database: str
    redis: str
    chromadb: str
    ollama: str
    uptime_seconds: float


class SystemStatsResponse(BaseModel):
    total_agents: int = 0
    running_agents: int = 0
    total_tasks: int = 0
    pending_tasks: int = 0
    total_skills: int = 0
    total_memories: int = 0
    total_system_logs: int = 0
