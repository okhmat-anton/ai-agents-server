import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, func, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


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


class ModelRoleAssignment(Base):
    __tablename__ = "model_role_assignments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    model_config_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("model_configs.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
