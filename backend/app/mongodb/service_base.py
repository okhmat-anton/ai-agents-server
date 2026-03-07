"""MongoDB services for CRUD operations."""
from typing import TypeVar, Generic, List, Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)


class BaseMongoService(Generic[T]):
    """Base service for MongoDB CRUD operations."""
    
    def __init__(self, db: AsyncIOMotorDatabase, collection_name: str, model_class: type[T]):
        self.db = db
        self.collection = db[collection_name]
        self.model_class = model_class
    
    async def create(self, model: T) -> T:
        """Create a new document."""
        doc = model.to_mongo()
        await self.collection.insert_one(doc)
        return model
    
    async def get_by_id(self, id: str) -> Optional[T]:
        """Get document by ID."""
        doc = await self.collection.find_one({"_id": id})
        return self.model_class.from_mongo(doc) if doc else None
    
    async def get_all(self, filter: Optional[Dict[str, Any]] = None, 
                     skip: int = 0, limit: int = 100) -> List[T]:
        """Get all documents with optional filter."""
        filter = filter or {}
        cursor = self.collection.find(filter).skip(skip).limit(limit)
        docs = await cursor.to_list(length=limit)
        return [self.model_class.from_mongo(doc) for doc in docs]
    
    async def update(self, id: str, update_data: Dict[str, Any]) -> Optional[T]:
        """Update document by ID."""
        result = await self.collection.find_one_and_update(
            {"_id": id},
            {"$set": update_data},
            return_document=True
        )
        return self.model_class.from_mongo(result) if result else None
    
    async def delete(self, id: str) -> bool:
        """Delete document by ID."""
        result = await self.collection.delete_one({"_id": id})
        return result.deleted_count > 0
    
    async def count(self, filter: Optional[Dict[str, Any]] = None) -> int:
        """Count documents with optional filter."""
        filter = filter or {}
        return await self.collection.count_documents(filter)
    
    async def find_one(self, filter: Dict[str, Any]) -> Optional[T]:
        """Find one document by filter."""
        doc = await self.collection.find_one(filter)
        return self.model_class.from_mongo(doc) if doc else None
