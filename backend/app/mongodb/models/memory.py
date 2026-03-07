"""MongoDB Memory models."""
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class MongoMemory(BaseModel):
    """Memory model for MongoDB."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str
    type: str = "fact"  # fact, summary, experience, note, hypothesis
    title: str
    content: str
    source: str = "agent"  # agent, user, system
    importance: float = 0.5
    tags: List[str] = Field(default_factory=list)
    category: str = "general"  # general, knowledge, task_result, error, skill, conversation
    task_id: Optional[str] = None
    embedding_id: Optional[str] = None
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    is_pinned: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def to_mongo(self) -> dict:
        doc = self.model_dump()
        doc["_id"] = doc.pop("id")
        doc["created_at"] = doc["created_at"].isoformat()
        doc["updated_at"] = doc["updated_at"].isoformat()
        if doc.get("last_accessed"):
            doc["last_accessed"] = doc["last_accessed"].isoformat()
        return doc

    @classmethod
    def from_mongo(cls, doc: dict) -> "MongoMemory":
        if not doc:
            return None
        doc["id"] = doc.pop("_id")
        if isinstance(doc.get("created_at"), str):
            doc["created_at"] = datetime.fromisoformat(doc["created_at"])
        if isinstance(doc.get("updated_at"), str):
            doc["updated_at"] = datetime.fromisoformat(doc["updated_at"])
        if isinstance(doc.get("last_accessed"), str):
            doc["last_accessed"] = datetime.fromisoformat(doc["last_accessed"])
        return cls(**doc)


class MongoMemoryLink(BaseModel):
    """Memory link model for MongoDB."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str
    source_id: str
    target_id: str
    relation_type: str  # causes, caused_by, depends_on, related_to, contradicts, supports, etc.
    strength: float = 0.5
    description: Optional[str] = None
    created_by: str = "agent"  # agent, system, user
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def to_mongo(self) -> dict:
        doc = self.model_dump()
        doc["_id"] = doc.pop("id")
        doc["created_at"] = doc["created_at"].isoformat()
        return doc

    @classmethod
    def from_mongo(cls, doc: dict) -> "MongoMemoryLink":
        if not doc:
            return None
        doc["id"] = doc.pop("_id")
        if isinstance(doc.get("created_at"), str):
            doc["created_at"] = datetime.fromisoformat(doc["created_at"])
        return cls(**doc)
