import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, func, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class AgentProtocol(Base):
    """
    Join table: one Agent can use many ThinkingProtocols.
    One of them is marked as the main (orchestrator) protocol.
    """
    __tablename__ = "agent_protocols"
    __table_args__ = (
        UniqueConstraint("agent_id", "protocol_id", name="uq_agent_protocol"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    protocol_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("thinking_protocols.id", ondelete="CASCADE"), nullable=False, index=True)
    is_main: Mapped[bool] = mapped_column(Boolean, default=False)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    agent = relationship("Agent", back_populates="agent_protocols")
    protocol = relationship("ThinkingProtocol", lazy="selectin")
