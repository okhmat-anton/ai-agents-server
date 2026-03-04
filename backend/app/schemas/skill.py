from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class SkillCreate(BaseModel):
    name: str
    display_name: str
    description: str = ""
    category: str = "general"
    version: str = "1.0.0"
    code: str = ""
    input_schema: dict = {}
    output_schema: dict = {}
    is_shared: bool = False


class SkillUpdate(BaseModel):
    name: str | None = None
    display_name: str | None = None
    description: str | None = None
    category: str | None = None
    version: str | None = None
    code: str | None = None
    input_schema: dict | None = None
    output_schema: dict | None = None
    is_shared: bool | None = None


class SkillResponse(BaseModel):
    id: UUID
    name: str
    display_name: str
    description: str
    category: str
    version: str
    code: str
    input_schema: dict
    output_schema: dict
    is_system: bool
    is_shared: bool
    author_agent_id: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AgentSkillCreate(BaseModel):
    skill_id: UUID
    config: dict | None = None


class AgentSkillResponse(BaseModel):
    skill_id: UUID
    agent_id: UUID
    is_enabled: bool
    config: dict | None
    added_at: datetime
    skill: SkillResponse | None = None

    model_config = {"from_attributes": True}
