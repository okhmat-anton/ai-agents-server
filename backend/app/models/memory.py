import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, func, Text, Float, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Memory(Base):
    __tablename__ = "memories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(30), default="fact")  # fact, summary, experience, note, hypothesis
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(20), default="agent")  # agent, user, system
    importance: Mapped[float] = mapped_column(Float, default=0.5)
    tags: Mapped[list | None] = mapped_column(ARRAY(String), default=[])
    category: Mapped[str] = mapped_column(String(30), default="general")  # general, knowledge, task_result, error, skill, conversation
    task_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True)
    embedding_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    access_count: Mapped[int] = mapped_column(Integer, default=0)
    last_accessed: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    agent = relationship("Agent", back_populates="memories")
    outgoing_links = relationship("MemoryLink", foreign_keys="MemoryLink.source_id", back_populates="source_memory", cascade="all, delete-orphan")
    incoming_links = relationship("MemoryLink", foreign_keys="MemoryLink.target_id", back_populates="target_memory", cascade="all, delete-orphan")


class MemoryLink(Base):
    __tablename__ = "memory_links"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("memories.id", ondelete="CASCADE"), nullable=False, index=True)
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("memories.id", ondelete="CASCADE"), nullable=False, index=True)
    relation_type: Mapped[str] = mapped_column(String(30), nullable=False)  # causes, caused_by, depends_on, related_to, contradicts, supports, derived_from, part_of, supersedes, example_of, precedes, follows
    strength: Mapped[float] = mapped_column(Float, default=0.5)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(20), default="agent")  # agent, system, user
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    source_memory = relationship("Memory", foreign_keys=[source_id], back_populates="outgoing_links")
    target_memory = relationship("Memory", foreign_keys=[target_id], back_populates="incoming_links")
