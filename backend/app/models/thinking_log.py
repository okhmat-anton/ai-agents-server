"""
ThinkingLog — captures a complete agent reasoning iteration
from receiving user input to producing a final response.
Each iteration contains multiple steps with detailed metadata.
"""
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, func, Text, Integer, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class ThinkingLog(Base):
    """One complete thinking iteration: user message → agent response."""
    __tablename__ = "thinking_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    message_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)  # the assistant message produced

    # What triggered this thinking
    user_input: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # Final output
    agent_output: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Model used
    model_name: Mapped[str | None] = mapped_column(String(300), nullable=True)

    # Stats
    total_duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    llm_calls_count: Mapped[int] = mapped_column(Integer, default=0)  # how many LLM calls in this iteration

    # Status: started, completed, error
    status: Mapped[str] = mapped_column(String(20), default="started")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    steps = relationship("ThinkingStep", back_populates="thinking_log", cascade="all, delete-orphan",
                         order_by="ThinkingStep.step_order", lazy="selectin")


class ThinkingStep(Base):
    """Individual step within a thinking iteration."""
    __tablename__ = "thinking_steps"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thinking_log_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("thinking_logs.id", ondelete="CASCADE"), nullable=False, index=True)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)

    # Step type: config_load, prompt_build, llm_call, response_parse, skill_exec, follow_up_call, protocol_update, error
    step_type: Mapped[str] = mapped_column(String(30), nullable=False)
    step_name: Mapped[str] = mapped_column(String(200), nullable=False)

    # Duration for this step
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)

    # Input/output for this step (flexible JSONB)
    input_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)   # what went in
    output_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # what came out

    # Status: started, completed, error, skipped
    status: Mapped[str] = mapped_column(String(20), default="completed")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    thinking_log = relationship("ThinkingLog", back_populates="steps")
