"""MongoDB ModelConfig models."""
import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# All available model roles
MODEL_ROLES = [
    "understanding",       # Понимание запроса
    "planning",            # Планирование действий
    "code_generation",     # Генерация кода
    "text_documents",      # Работа с текстом и документами
    "data_analysis",       # Анализ данных
    "embedding",           # Поиск (эмбеддинг модель)
    "json_output",         # Структурированный вывод json
    "creative",            # Креативная генерация
    "validation",          # Валидация и проверка качества
    "photo_analysis",      # Анализ фото
    "video_analysis",      # Анализ видео
    "sound_generation",    # Генерация звука
    "speech_recognition",  # Распознавание звука (перевод в текст)
    "translation",         # Перевод
    "dialog",              # Простой диалог
    "base",                # Базовая модель (fallback)
]

MODEL_ROLE_LABELS = {
    "understanding": "Понимание запроса",
    "planning": "Планирование действий",
    "code_generation": "Генерация кода",
    "text_documents": "Работа с текстом и документами",
    "data_analysis": "Анализ данных",
    "embedding": "Поиск (эмбеддинг)",
    "json_output": "Структурированный вывод JSON",
    "creative": "Креативная генерация",
    "validation": "Валидация и проверка качества",
    "photo_analysis": "Анализ фото",
    "video_analysis": "Анализ видео",
    "sound_generation": "Генерация звука",
    "speech_recognition": "Распознавание звука",
    "translation": "Перевод",
    "dialog": "Простой диалог",
    "base": "Базовая модель",
}


class MongoModelConfig(BaseModel):
    """LLM Model Configuration for MongoDB."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    provider: str  # ollama, openai_compatible
    base_url: str
    api_key: Optional[str] = None
    model_id: str
    is_active: bool = True
    is_primary: bool = False
    supports_vision: bool = False
    context_window: int = 8192
    max_output_tokens: int = 4096
    timeout: int = 180  # seconds, default 3 minutes
    retry_count: int = 3  # number of retries on failure
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def to_mongo(self) -> dict:
        doc = self.model_dump()
        doc["_id"] = doc.pop("id")
        doc["created_at"] = doc["created_at"].isoformat()
        doc["updated_at"] = doc["updated_at"].isoformat()
        return doc

    @classmethod
    def from_mongo(cls, doc: dict) -> "MongoModelConfig":
        if not doc:
            return None
        doc["id"] = doc.pop("_id")
        if isinstance(doc.get("created_at"), str):
            doc["created_at"] = datetime.fromisoformat(doc["created_at"])
        if isinstance(doc.get("updated_at"), str):
            doc["updated_at"] = datetime.fromisoformat(doc["updated_at"])
        return cls(**doc)


class MongoModelRoleAssignment(BaseModel):
    """Model Role Assignment for MongoDB."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: Optional[str] = None
    role: str  # main, vision, code, etc.
    model_config_id: str
    priority: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def to_mongo(self) -> dict:
        doc = self.model_dump()
        doc["_id"] = doc.pop("id")
        doc["created_at"] = doc["created_at"].isoformat()
        return doc

    @classmethod
    def from_mongo(cls, doc: dict) -> "MongoModelRoleAssignment":
        if not doc:
            return None
        doc["id"] = doc.pop("_id")
        if isinstance(doc.get("created_at"), str):
            doc["created_at"] = datetime.fromisoformat(doc["created_at"])
        return cls(**doc)
