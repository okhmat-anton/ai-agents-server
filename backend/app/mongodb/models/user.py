"""MongoDB User model."""
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class MongoUser(BaseModel):
    """User model for MongoDB."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    password_hash: str
    is_active: bool = True
    disclaimer_accepted_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def to_mongo(self) -> dict:
        """Convert to MongoDB document."""
        doc = self.model_dump()
        doc["_id"] = doc.pop("id")
        doc["created_at"] = doc["created_at"].isoformat()
        doc["updated_at"] = doc["updated_at"].isoformat()
        if doc.get("disclaimer_accepted_at"):
            doc["disclaimer_accepted_at"] = doc["disclaimer_accepted_at"].isoformat()
        return doc

    @classmethod
    def from_mongo(cls, doc: dict) -> "MongoUser":
        """Create from MongoDB document."""
        if not doc:
            return None
        doc["id"] = doc.pop("_id")
        if isinstance(doc.get("created_at"), str):
            doc["created_at"] = datetime.fromisoformat(doc["created_at"])
        if isinstance(doc.get("updated_at"), str):
            doc["updated_at"] = datetime.fromisoformat(doc["updated_at"])
        if isinstance(doc.get("disclaimer_accepted_at"), str):
            doc["disclaimer_accepted_at"] = datetime.fromisoformat(doc["disclaimer_accepted_at"])
        return cls(**doc)
