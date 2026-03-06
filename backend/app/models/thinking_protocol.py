import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, func, Text, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


PROTOCOL_TYPES = ("standard", "orchestrator", "loop")


class ThinkingProtocol(Base):
    """
    A thinking protocol defines a step-by-step reasoning workflow for agents.
    Types:
      standard     — a regular reasoning protocol (analysis, research, etc.)
      orchestrator — a meta-protocol that selects and delegates to child protocols
      loop         — an autonomous work protocol; the agent self-directs in cycles
    """
    __tablename__ = "thinking_protocols"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    type: Mapped[str] = mapped_column(String(20), default="standard")  # standard, orchestrator, loop
    steps: Mapped[dict] = mapped_column(JSONB, default=[])
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
