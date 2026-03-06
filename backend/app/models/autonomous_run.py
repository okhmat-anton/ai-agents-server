"""
AutonomousRun — tracks an autonomous agent work session.

An autonomous run is a series of self-directed cycles where the agent
decides what to do based on its loop protocol, beliefs, aspirations,
memories, and skills — without human input.

Modes:
  continuous — runs until manually stopped
  cycles     — runs a specified number of cycles
"""
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, func, Text, Integer, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class AutonomousRun(Base):
    """One autonomous work session for an agent."""
    __tablename__ = "autonomous_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="SET NULL"), nullable=True)

    # Run mode
    mode: Mapped[str] = mapped_column(String(20), nullable=False, default="continuous")  # continuous, cycles
    max_cycles: Mapped[int | None] = mapped_column(Integer, nullable=True)  # null = unlimited
    completed_cycles: Mapped[int] = mapped_column(Integer, default=0)

    # Protocol used for autonomous work
    loop_protocol_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("thinking_protocols.id", ondelete="SET NULL"), nullable=True)

    # Status: running, paused, completed, stopped, error
    status: Mapped[str] = mapped_column(String(20), default="running")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Cycle state — preserved between cycles
    cycle_state: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # todo_list, last_output, context

    # Stats
    total_duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_llm_calls: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    agent = relationship("Agent", lazy="selectin")
    session = relationship("ChatSession", lazy="selectin")
    loop_protocol = relationship("ThinkingProtocol", lazy="selectin")
