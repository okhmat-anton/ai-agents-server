"""Pydantic schemas for thinking logs API responses."""
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class ThinkingStepResponse(BaseModel):
    id: UUID
    step_order: int
    step_type: str
    step_name: str
    duration_ms: int
    input_data: dict | None = None
    output_data: dict | None = None
    status: str
    error_message: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ThinkingLogResponse(BaseModel):
    id: UUID
    agent_id: UUID
    session_id: UUID
    message_id: UUID | None = None
    user_input: str
    agent_output: str | None = None
    model_name: str | None = None
    total_duration_ms: int
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int
    llm_calls_count: int
    status: str
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
    steps: list[ThinkingStepResponse] = []

    model_config = {"from_attributes": True}


class ThinkingLogSummaryResponse(BaseModel):
    """Lighter version without steps, for list endpoints."""
    id: UUID
    agent_id: UUID
    session_id: UUID
    message_id: UUID | None = None
    user_input: str
    agent_output: str | None = None
    model_name: str | None = None
    total_duration_ms: int
    total_tokens: int
    llm_calls_count: int
    status: str
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
    steps_count: int = 0

    model_config = {"from_attributes": True}
