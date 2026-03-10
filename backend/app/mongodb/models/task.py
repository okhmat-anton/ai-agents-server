"""MongoDB Task and AutonomousRun models."""
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class MongoTask(BaseModel):
    """Task model for MongoDB."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    type: str = "one_time"  # one_time, recurring, trigger
    status: str = "pending"  # pending, running, completed, failed, cancelled
    priority: str = "normal"  # low, normal, high, critical
    schedule: Optional[str] = None  # Cron expression
    next_run_at: Optional[datetime] = None
    execute_at: Optional[datetime] = None
    trigger_type: Optional[str] = None
    trigger_config: Optional[Dict[str, Any]] = None
    max_retries: int = 3
    retry_count: int = 0
    timeout: int = 300
    parent_task_id: Optional[str] = None
    is_decomposed: bool = False
    ready_to_execute: bool = True
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def to_mongo(self) -> dict:
        doc = self.model_dump()
        doc["_id"] = doc.pop("id")
        doc["created_at"] = doc["created_at"].isoformat()
        doc["updated_at"] = doc["updated_at"].isoformat()
        if doc.get("started_at"):
            doc["started_at"] = doc["started_at"].isoformat()
        if doc.get("completed_at"):
            doc["completed_at"] = doc["completed_at"].isoformat()
        if doc.get("next_run_at"):
            doc["next_run_at"] = doc["next_run_at"].isoformat()
        return doc

    @classmethod
    def from_mongo(cls, doc: dict) -> "MongoTask":
        if not doc:
            return None
        doc["id"] = doc.pop("_id")
        if isinstance(doc.get("created_at"), str):
            doc["created_at"] = datetime.fromisoformat(doc["created_at"])
        if isinstance(doc.get("updated_at"), str):
            doc["updated_at"] = datetime.fromisoformat(doc["updated_at"])
        if isinstance(doc.get("started_at"), str):
            doc["started_at"] = datetime.fromisoformat(doc["started_at"])
        if isinstance(doc.get("completed_at"), str):
            doc["completed_at"] = datetime.fromisoformat(doc["completed_at"])
        if isinstance(doc.get("next_run_at"), str):
            doc["next_run_at"] = datetime.fromisoformat(doc["next_run_at"])
        return cls(**doc)


class MongoAutonomousRun(BaseModel):
    """Autonomous Run model for MongoDB — tracks autonomous agent work sessions."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str
    session_id: Optional[str] = None
    
    # Run mode
    mode: str = "continuous"  # continuous, cycles
    max_cycles: Optional[int] = None  # null = unlimited
    completed_cycles: int = 0
    
    # Protocol used for autonomous work
    loop_protocol_id: Optional[str] = None
    
    # Status: running, paused, completed, stopped, error
    status: str = "running"
    error_message: Optional[str] = None
    
    # Cycle state — preserved between cycles
    cycle_state: Optional[Dict[str, Any]] = None  # todo_list, last_output, context
    
    # Stats
    total_duration_ms: int = 0
    total_tokens: int = 0
    total_llm_calls: int = 0
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_mongo(self) -> dict:
        doc = self.model_dump()
        doc["_id"] = doc.pop("id")
        doc["created_at"] = doc["created_at"].isoformat()
        if doc.get("started_at"):
            doc["started_at"] = doc["started_at"].isoformat()
        if doc.get("completed_at"):
            doc["completed_at"] = doc["completed_at"].isoformat()
        return doc

    @classmethod
    def from_mongo(cls, doc: dict) -> "MongoAutonomousRun":
        if not doc:
            return None
        doc["id"] = doc.pop("_id")
        if isinstance(doc.get("created_at"), str):
            doc["created_at"] = datetime.fromisoformat(doc["created_at"])
        if isinstance(doc.get("started_at"), str):
            doc["started_at"] = datetime.fromisoformat(doc["started_at"])
        if isinstance(doc.get("completed_at"), str):
            doc["completed_at"] = datetime.fromisoformat(doc["completed_at"])
        return cls(**doc)
