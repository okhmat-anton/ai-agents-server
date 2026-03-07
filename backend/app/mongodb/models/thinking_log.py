"""MongoDB ThinkingLog models."""
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class MongoThinkingLog(BaseModel):
    """One complete thinking iteration: user message → agent response."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str
    session_id: str
    message_id: Optional[str] = None  # the assistant message produced

    # What triggered this thinking
    user_input: str = ""
    # Final output
    agent_output: Optional[str] = None

    # Model used
    model_name: Optional[str] = None

    # Stats
    total_duration_ms: int = 0
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    llm_calls_count: int = 0

    # Status: started, completed, error
    status: str = "started"
    error_message: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    def to_mongo(self) -> dict:
        doc = self.model_dump()
        doc["_id"] = doc.pop("id")
        doc["created_at"] = doc["created_at"].isoformat()
        if doc.get("completed_at"):
            doc["completed_at"] = doc["completed_at"].isoformat()
        return doc

    @classmethod
    def from_mongo(cls, doc: dict) -> "MongoThinkingLog":
        if not doc:
            return None
        doc["id"] = doc.pop("_id")
        if isinstance(doc.get("created_at"), str):
            doc["created_at"] = datetime.fromisoformat(doc["created_at"])
        if isinstance(doc.get("completed_at"), str):
            doc["completed_at"] = datetime.fromisoformat(doc["completed_at"])
        return cls(**doc)


class MongoThinkingStep(BaseModel):
    """Individual step within a thinking iteration."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    thinking_log_id: str
    step_order: int
    step_type: str  # config_load, prompt_build, llm_call, response_parse, skill_exec, follow_up_call, protocol_update, error
    step_name: str

    # Duration for this step
    duration_ms: int = 0

    # Input/output for this step (flexible dicts)
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None

    # Status: started, completed, error, skipped
    status: str = "completed"
    error_message: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)

    def to_mongo(self) -> dict:
        doc = self.model_dump()
        doc["_id"] = doc.pop("id")
        doc["created_at"] = doc["created_at"].isoformat()
        return doc

    @classmethod
    def from_mongo(cls, doc: dict) -> "MongoThinkingStep":
        if not doc:
            return None
        doc["id"] = doc.pop("_id")
        if isinstance(doc.get("created_at"), str):
            doc["created_at"] = datetime.fromisoformat(doc["created_at"])
        return cls(**doc)
