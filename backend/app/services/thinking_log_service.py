"""
Thinking Log Service — captures detailed agent reasoning traces.

Usage within chat.py:
    tracker = ThinkingTracker(db, agent_id, session_id, user_input)
    await tracker.start()

    await tracker.step("config_load", "Loading agent config", input_data={...}, output_data={...})
    await tracker.step("prompt_build", "Building system prompt", ...)
    await tracker.step("llm_call", "LLM inference", ...)

    await tracker.complete(agent_output, message_id, model_name, total_tokens, ...)
    # or
    await tracker.fail(error_message)
"""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.thinking_log import ThinkingLog, ThinkingStep


class ThinkingTracker:
    """Context manager-style tracker for a single thinking iteration."""

    def __init__(
        self,
        db: AsyncSession,
        agent_id: uuid.UUID,
        session_id: uuid.UUID,
        user_input: str,
    ):
        self.db = db
        self.agent_id = agent_id
        self.session_id = session_id
        self.user_input = user_input
        self.log: ThinkingLog | None = None
        self._step_order = 0
        self._start_time = 0.0
        self._step_start = 0.0

    async def start(self) -> ThinkingLog:
        """Create the thinking log entry in DB."""
        self._start_time = time.monotonic()
        self.log = ThinkingLog(
            agent_id=self.agent_id,
            session_id=self.session_id,
            user_input=self.user_input[:2000],  # truncate very long inputs
            status="started",
        )
        self.db.add(self.log)
        await self.db.flush()
        return self.log

    async def step(
        self,
        step_type: str,
        step_name: str,
        *,
        input_data: dict | None = None,
        output_data: dict | None = None,
        status: str = "completed",
        error_message: str | None = None,
        duration_ms: int | None = None,
    ) -> ThinkingStep:
        """Record a single step in the thinking process."""
        if not self.log:
            await self.start()

        self._step_order += 1

        step = ThinkingStep(
            thinking_log_id=self.log.id,
            step_order=self._step_order,
            step_type=step_type,
            step_name=step_name,
            input_data=_safe_jsonb(input_data),
            output_data=_safe_jsonb(output_data),
            status=status,
            error_message=error_message,
            duration_ms=duration_ms or 0,
        )
        self.db.add(step)
        await self.db.flush()
        return step

    def start_step_timer(self):
        """Start a timer for measuring step duration."""
        self._step_start = time.monotonic()

    def elapsed_step_ms(self) -> int:
        """Get ms since last start_step_timer."""
        return int((time.monotonic() - self._step_start) * 1000)

    async def complete(
        self,
        agent_output: str,
        *,
        message_id: uuid.UUID | None = None,
        model_name: str | None = None,
        total_tokens: int = 0,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        llm_calls_count: int = 1,
    ) -> ThinkingLog:
        """Mark the thinking log as completed."""
        if not self.log:
            return None

        total_ms = int((time.monotonic() - self._start_time) * 1000)
        
        self.log.agent_output = agent_output[:5000] if agent_output else None  # truncate
        self.log.message_id = message_id
        self.log.model_name = model_name
        self.log.total_duration_ms = total_ms
        self.log.total_tokens = total_tokens
        self.log.prompt_tokens = prompt_tokens
        self.log.completion_tokens = completion_tokens
        self.log.llm_calls_count = llm_calls_count
        self.log.status = "completed"
        self.log.completed_at = datetime.now(timezone.utc)
        await self.db.flush()
        return self.log

    async def fail(self, error_message: str) -> ThinkingLog:
        """Mark the thinking log as failed."""
        if not self.log:
            return None

        total_ms = int((time.monotonic() - self._start_time) * 1000)
        self.log.total_duration_ms = total_ms
        self.log.status = "error"
        self.log.error_message = error_message
        self.log.completed_at = datetime.now(timezone.utc)
        await self.db.flush()
        return self.log


def _safe_jsonb(data: dict | None) -> dict | None:
    """Ensure data is JSON-serializable and not too large."""
    if data is None:
        return None
    # Truncate very large string values to keep DB manageable
    result = {}
    for k, v in data.items():
        if isinstance(v, str) and len(v) > 3000:
            result[k] = v[:3000] + "... [truncated]"
        elif isinstance(v, list) and len(v) > 50:
            result[k] = v[:50]
            result[f"_{k}_total"] = len(v)
        else:
            result[k] = v
    return result
