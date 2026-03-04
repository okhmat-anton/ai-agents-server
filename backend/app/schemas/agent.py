from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class AgentCreate(BaseModel):
    name: str
    description: str | None = None
    model_id: UUID
    model_name: str = "qwen2.5-coder:14b"
    system_prompt: str = ""
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 40
    max_tokens: int = 2048
    num_ctx: int = 32768
    repeat_penalty: float = 1.1
    num_predict: int = -1
    stop: list[str] = []
    num_thread: int = 8
    num_gpu: int = 1


class AgentUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    model_id: UUID | None = None
    model_name: str | None = None
    system_prompt: str | None = None
    temperature: float | None = None
    top_p: float | None = None
    top_k: int | None = None
    max_tokens: int | None = None
    num_ctx: int | None = None
    repeat_penalty: float | None = None
    num_predict: int | None = None
    stop: list[str] | None = None
    num_thread: int | None = None
    num_gpu: int | None = None


class AgentResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    model_id: UUID
    model_name: str
    system_prompt: str
    status: str
    temperature: float
    top_p: float
    top_k: int
    max_tokens: int
    num_ctx: int
    repeat_penalty: float
    num_predict: int
    stop: list[str] | None
    num_thread: int
    num_gpu: int
    created_at: datetime
    updated_at: datetime
    last_run_at: datetime | None

    model_config = {"from_attributes": True}


class AgentStatsResponse(BaseModel):
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    total_logs: int = 0
    total_memories: int = 0
    total_skills: int = 0
