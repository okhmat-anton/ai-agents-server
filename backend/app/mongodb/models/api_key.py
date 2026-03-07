"""MongoDB ApiKey model."""
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class MongoApiKey(BaseModel):
    """API Key model for MongoDB."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    name: str
    key: str
    is_active: bool = True
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def to_mongo(self) -> dict:
        """Convert to MongoDB document."""
        doc = self.model_dump()
        doc["_id"] = doc.pop("id")
        doc["created_at"] = doc["created_at"].isoformat()
        if doc.get("last_used_at"):
            doc["last_used_at"] = doc["last_used_at"].isoformat()
        if doc.get("expires_at"):
            doc["expires_at"] = doc["expires_at"].isoformat()
        return doc

    @classmethod
    def from_mongo(cls, doc: dict) -> "MongoApiKey":
        """Create from MongoDB document."""
        if not doc:
            return None
        doc["id"] = doc.pop("_id")
        if isinstance(doc.get("created_at"), str):
            doc["created_at"] = datetime.fromisoformat(doc["created_at"])
        if isinstance(doc.get("last_used_at"), str):
            doc["last_used_at"] = datetime.fromisoformat(doc["last_used_at"])
        if isinstance(doc.get("expires_at"), str):
            doc["expires_at"] = datetime.fromisoformat(doc["expires_at"])
        return cls(**doc)
