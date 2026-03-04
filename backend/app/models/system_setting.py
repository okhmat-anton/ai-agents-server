"""
SystemSetting — key-value store for system-level settings.
"""
import uuid
from sqlalchemy import Column, String, Text
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class SystemSetting(Base):
    __tablename__ = "system_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(String(128), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=False, default="")
    description = Column(Text, nullable=True)
