"""MongoDB Log models."""
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class MongoAgentLog(BaseModel):
    """Agent log entry for MongoDB."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str
    level: str = "info"  # debug, info, warning, error, critical
    message: str
    metadata_: Optional[Dict[str, Any]] = Field(default=None, alias="metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"populate_by_name": True}

    def to_mongo(self) -> dict:
        doc = self.model_dump(by_alias=True)
        doc["_id"] = doc.pop("id")
        doc["created_at"] = doc["created_at"].isoformat()
        return doc

    @classmethod
    def from_mongo(cls, doc: dict) -> "MongoAgentLog":
        if not doc:
            return None
        doc["id"] = doc.pop("_id")
        if isinstance(doc.get("created_at"), str):
            doc["created_at"] = datetime.fromisoformat(doc["created_at"])
        return cls(**doc)
