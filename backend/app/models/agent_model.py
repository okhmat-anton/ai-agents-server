import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, func, Text, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class AgentModel(Base):
    """
    Join table: one Agent can use many Models.
    Each entry describes *why / when* this model is used by the agent.
    """
    __tablename__ = "agent_models"
    __table_args__ = (
        UniqueConstraint("agent_id", "model_config_id", name="uq_agent_model"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    model_config_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("model_configs.id", ondelete="CASCADE"), nullable=False, index=True)

    task_type: Mapped[str] = mapped_column(Text, nullable=False, default="general")  # e.g. "code generation", "text analysis"
    tags: Mapped[list | None] = mapped_column(ARRAY(String), default=[])  # e.g. ["code", "fast", "large-context"]
    priority: Mapped[int] = mapped_column(Integer, default=0)  # lower = higher priority (0 = default / primary)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    agent = relationship("Agent", back_populates="agent_models")
    model_config_rel = relationship("ModelConfig", lazy="selectin")
