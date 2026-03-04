from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class ModelConfigCreate(BaseModel):
    name: str
    model_id: str = ""
    provider: str = "ollama"
    base_url: str = "http://host.docker.internal:11434"
    api_key: str | None = None
    is_active: bool = True


class ModelConfigUpdate(BaseModel):
    name: str | None = None
    model_id: str | None = None
    provider: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    is_active: bool | None = None


class ModelConfigResponse(BaseModel):
    id: UUID
    name: str
    model_id: str
    provider: str
    base_url: str
    api_key: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ApiKeyCreate(BaseModel):
    name: str
    description: str | None = None


class ApiKeyResponse(BaseModel):
    id: UUID
    name: str
    key_prefix: str
    description: str | None
    last_used_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiKeyCreatedResponse(ApiKeyResponse):
    key: str  # Full key shown only once


# --- System Settings ---
class SystemSettingResponse(BaseModel):
    key: str
    value: str
    description: str | None = None

    model_config = {"from_attributes": True}


class SystemSettingUpdate(BaseModel):
    value: str
