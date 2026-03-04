import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, func, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    description_for_agent: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(30), default="general")  # general, web, files, code, data, custom
    version: Mapped[str] = mapped_column(String(20), default="1.0.0")
    code: Mapped[str] = mapped_column(Text, nullable=False, default="")
    input_schema: Mapped[dict] = mapped_column(JSONB, default={})
    output_schema: Mapped[dict] = mapped_column(JSONB, default={})
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    is_shared: Mapped[bool] = mapped_column(Boolean, default=False)
    author_agent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    agent_skills = relationship("AgentSkill", back_populates="skill", cascade="all, delete-orphan")


class AgentSkill(Base):
    __tablename__ = "agent_skills"

    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), primary_key=True)
    skill_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    agent = relationship("Agent", back_populates="agent_skills")
    skill = relationship("Skill", back_populates="agent_skills")
