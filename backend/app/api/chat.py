"""
Chat API — persistent chat sessions with single/multi-model support.
Integrates protocol execution: orchestrator delegation, todo tracking, skill invocation.
"""
import asyncio
import json
import time
import uuid
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.config import get_settings
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.model_config import ModelConfig
from app.models.agent import Agent
from app.models.agent_model import AgentModel
from app.models.agent_protocol import AgentProtocol
from app.models.skill import Skill, AgentSkill
from app.models.chat import ChatSession, ChatMessage
from app.llm.base import Message, GenerationParams, LLMResponse
from app.llm.ollama import OllamaProvider
from app.llm.openai_compatible import OpenAICompatibleProvider
from app.api.agent_files import read_agent_config, read_agent_settings
from app.api.agent_beliefs import read_beliefs
from app.services.protocol_executor import (
    build_agent_system_prompt,
    format_child_protocol_prompt,
    parse_skill_invocations,
    parse_todo_list,
    parse_delegate,
)
from app.services.thinking_log_service import ThinkingTracker

router = APIRouter(prefix="/api/chat", tags=["chat"])


# ── Schemas ──────────────────────────────────────────────

class ChatSessionCreate(BaseModel):
    title: str = "New Chat"
    model_ids: list[str] = []          # model_config UUIDs or "ollama:modelname"
    agent_id: Optional[str] = None
    multi_model: bool = False
    system_prompt: Optional[str] = None
    temperature: float = 0.7


class ChatSessionUpdate(BaseModel):
    title: Optional[str] = None
    model_ids: Optional[list[str]] = None
    multi_model: Optional[bool] = None
    system_prompt: Optional[str] = None
    temperature: Optional[float] = None


class ChatSessionResponse(BaseModel):
    id: str
    title: str
    model_ids: list[str]
    agent_id: Optional[str] = None
    multi_model: bool
    system_prompt: Optional[str] = None
    temperature: float
    message_count: int = 0
    created_at: str
    updated_at: str
    last_message: Optional[str] = None

    model_config = {"from_attributes": True}


class ChatMessageResponse(BaseModel):
    id: str
    role: str
    content: str
    model_name: Optional[str] = None
    model_responses: Optional[dict] = None
    total_tokens: int = 0
    duration_ms: int = 0
    created_at: str


class SendMessageRequest(BaseModel):
    content: str
    # Override models for this message (optional)
    model_ids: Optional[list[str]] = None


class AvailableModel(BaseModel):
    id: str
    name: str
    model_id: str
    provider: str
    type: str = "model"  # "model" or "agent"


# ── Helpers ──────────────────────────────────────────────

def _session_to_response(session: ChatSession) -> dict:
    msgs = session.messages or []
    last_msg = None
    if msgs:
        last = msgs[-1]
        last_msg = last.content[:100] if last.content else None
    return {
        "id": str(session.id),
        "title": session.title,
        "model_ids": session.model_ids or [],
        "agent_id": str(session.agent_id) if session.agent_id else None,
        "multi_model": session.multi_model,
        "system_prompt": session.system_prompt,
        "temperature": session.temperature,
        "protocol_state": session.protocol_state,
        "message_count": len(msgs),
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
        "last_message": last_msg,
    }


def _message_to_response(msg: ChatMessage) -> dict:
    return {
        "id": str(msg.id),
        "role": msg.role,
        "content": msg.content,
        "model_name": msg.model_name,
        "model_responses": msg.model_responses,
        "total_tokens": msg.total_tokens,
        "duration_ms": msg.duration_ms,
        "metadata": msg.msg_metadata,
        "created_at": msg.created_at.isoformat(),
    }


async def _resolve_model(model_id_str: str, db: AsyncSession) -> tuple[str, str, str, str | None]:
    """Resolve a model_id string to (provider, base_url, model_name, api_key).
    model_id_str can be:
      - UUID of a model_config
      - 'ollama:model_name' for direct ollama model
    """
    if model_id_str.startswith("ollama:"):
        model_name = model_id_str[7:]
        settings = get_settings()
        return ("ollama", settings.OLLAMA_BASE_URL, model_name, None)

    try:
        uid = uuid.UUID(model_id_str)
    except ValueError:
        # Treat as ollama model name directly
        settings = get_settings()
        return ("ollama", settings.OLLAMA_BASE_URL, model_id_str, None)

    result = await db.execute(select(ModelConfig).where(ModelConfig.id == uid))
    mc = result.scalar_one_or_none()
    if not mc:
        raise HTTPException(status_code=404, detail=f"Model config {model_id_str} not found")

    # For ollama models, always use current OLLAMA_BASE_URL (may differ between Docker / dev)
    if mc.provider == "ollama":
        settings = get_settings()
        return (mc.provider, settings.OLLAMA_BASE_URL, mc.model_id, mc.api_key)

    return (mc.provider, mc.base_url, mc.model_id, mc.api_key)


async def _chat_with_model(
    provider: str, base_url: str, model_name: str, api_key: str | None,
    messages: list[dict], params: GenerationParams | None = None,
) -> LLMResponse:
    """Send chat to a single model and return response."""
    llm_messages = [Message(role=m["role"], content=m["content"]) for m in messages]
    if params is None:
        params = GenerationParams()

    if provider == "ollama":
        llm = OllamaProvider(base_url)
    else:
        llm = OpenAICompatibleProvider(base_url, api_key)

    return await llm.chat(model_name, llm_messages, params)


# ── Endpoints ────────────────────────────────────────────

@router.get("/available-models")
async def get_available_models(
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all available models (from model configs + running ollama models) and agents."""
    models = []

    # 1. From model_configs
    result = await db.execute(select(ModelConfig).where(ModelConfig.is_active == True))
    for mc in result.scalars().all():
        models.append({
            "id": str(mc.id),
            "name": mc.name,
            "model_id": mc.model_id,
            "provider": mc.provider,
            "type": "model",
        })

    # 2. Running ollama models (add ones not already in model_configs)
    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            if r.status_code == 200:
                known_model_ids = {m["model_id"] for m in models if m["provider"] == "ollama"}
                for om in r.json().get("models", []):
                    if om["name"] not in known_model_ids:
                        models.append({
                            "id": f"ollama:{om['name']}",
                            "name": om["name"],
                            "model_id": om["name"],
                            "provider": "ollama",
                            "type": "model",
                        })
    except Exception:
        pass

    # 3. Agents
    result = await db.execute(select(Agent))
    for agent in result.scalars().all():
        models.append({
            "id": f"agent:{agent.id}",
            "name": f"🤖 {agent.name}",
            "model_id": "",
            "provider": "agent",
            "type": "agent",
        })

    return models


# ── Sessions CRUD ────────────────────────────────────────

@router.get("/sessions")
async def list_sessions(
    limit: int = Query(50, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List chat sessions, newest first."""
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == user.id)
        .order_by(ChatSession.updated_at.desc())
        .limit(limit)
    )
    sessions = result.scalars().all()
    return [_session_to_response(s) for s in sessions]


@router.post("/sessions")
async def create_session(
    body: ChatSessionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new chat session."""
    agent_id = None
    model_ids = list(body.model_ids)

    # Extract agent_id from explicit field
    if body.agent_id and body.agent_id.startswith("agent:"):
        try:
            agent_id = uuid.UUID(body.agent_id[6:])
        except ValueError:
            pass
    elif body.agent_id:
        try:
            agent_id = uuid.UUID(body.agent_id)
        except ValueError:
            pass

    # Also detect agent: prefix inside model_ids
    if not agent_id:
        for mid in model_ids:
            if mid.startswith("agent:"):
                try:
                    agent_id = uuid.UUID(mid[6:])
                except ValueError:
                    pass
                break

    # If agent selected, resolve the agent's actual model(s) for LLM calls
    if agent_id:
        # Remove agent: entries from model_ids
        model_ids = [m for m in model_ids if not m.startswith("agent:")]

        # If no real models left, resolve from agent's configuration
        if not model_ids:
            agent = await db.get(Agent, agent_id)
            if agent:
                # Use agent_models (multi-model support) or fallback to agent.model_id
                if agent.agent_models:
                    model_ids = [str(am.model_config_id) for am in sorted(agent.agent_models, key=lambda x: x.priority)]
                elif agent.model_id:
                    model_ids = [str(agent.model_id)]

        if not model_ids:
            raise HTTPException(status_code=400, detail="Agent has no models configured")

    session = ChatSession(
        user_id=user.id,
        title=body.title,
        model_ids=model_ids,
        agent_id=agent_id,
        multi_model=body.multi_model,
        system_prompt=body.system_prompt,
        temperature=body.temperature,
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)
    return _session_to_response(session)


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get session with all messages."""
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == uuid.UUID(session_id),
            ChatSession.user_id == user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    data = _session_to_response(session)
    data["messages"] = [_message_to_response(m) for m in session.messages]
    return data


@router.put("/sessions/{session_id}")
async def update_session(
    session_id: str,
    body: ChatSessionUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update session settings."""
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == uuid.UUID(session_id),
            ChatSession.user_id == user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if body.title is not None:
        session.title = body.title
    if body.model_ids is not None:
        session.model_ids = body.model_ids
    if body.multi_model is not None:
        session.multi_model = body.multi_model
    if body.system_prompt is not None:
        session.system_prompt = body.system_prompt
    if body.temperature is not None:
        session.temperature = body.temperature

    await db.flush()
    await db.refresh(session)
    return _session_to_response(session)


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a chat session and all its messages."""
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == uuid.UUID(session_id),
            ChatSession.user_id == user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    await db.delete(session)
    return {"message": "Session deleted"}


# ── Send Message ─────────────────────────────────────────

async def _load_agent_protocols(agent: Agent, db: AsyncSession) -> list[dict]:
    """Load all protocols assigned to an agent."""
    protocols = []
    for ap in (agent.agent_protocols or []):
        p = ap.protocol
        if p:
            protocols.append({
                "id": str(p.id),
                "name": p.name,
                "description": p.description or "",
                "type": p.type or "standard",
                "steps": p.steps or [],
                "is_main": ap.is_main,
                "priority": ap.priority,
            })
    return protocols


async def _load_agent_skills(agent_id: uuid.UUID, db: AsyncSession, agent: "Agent" = None) -> list[dict]:
    """Load all enabled skills for an agent.

    An agent has access to:
    - All system skills (is_system=true)
    - All shared/public skills (is_shared=true)
    - Agent's personal skills (author_agent_id=agent_id)

    Skills explicitly disabled via AgentSkill(is_enabled=false) are excluded.
    Skills requiring filesystem/system access are excluded if not permitted
    (both globally and at agent level).
    """
    from sqlalchemy import or_
    from app.api.settings import get_setting_value

    # Determine effective permissions (global AND agent-level)
    global_fs = (await get_setting_value(db, "filesystem_access_enabled")) == "true"
    global_sys = (await get_setting_value(db, "system_access_enabled")) == "true"
    agent_fs = agent.filesystem_access if agent else False
    agent_sys = agent.system_access if agent else False
    effective_fs = global_fs and agent_fs
    effective_sys = global_sys and agent_sys

    # Skills that require specific permissions
    FS_SKILLS = {"file_read", "file_write"}
    SYS_SKILLS = {"shell_exec", "code_execute"}

    # Get all potentially available skills
    result = await db.execute(
        select(Skill).where(
            or_(
                Skill.is_system == True,
                Skill.is_shared == True,
                Skill.author_agent_id == agent_id,
            )
        )
    )
    all_skills = result.scalars().all()

    # Check disabled state from agent_skills table
    result = await db.execute(
        select(AgentSkill).where(
            AgentSkill.agent_id == agent_id,
            AgentSkill.is_enabled == False,
        )
    )
    disabled_ids = {str(ask.skill_id) for ask in result.scalars().all()}

    skills = []
    for s in all_skills:
        if str(s.id) in disabled_ids:
            continue
        # Permission gating: skip fs/sys skills if access not granted
        if s.name in FS_SKILLS and not effective_fs:
            continue
        if s.name in SYS_SKILLS and not effective_sys:
            continue
        skills.append({
            "id": str(s.id),
            "name": s.name,
            "display_name": s.display_name,
            "description": s.description or "",
            "description_for_agent": s.description_for_agent or "",
            "category": s.category,
            "code": s.code,
            "input_schema": s.input_schema or {},
        })
    return skills


async def _execute_skill(skill_name: str, args: dict, agent_skills: list[dict]) -> dict:
    """Execute a skill by name and return the result."""
    skill = None
    for s in agent_skills:
        if s["name"] == skill_name:
            skill = s
            break

    if not skill:
        return {"error": f"Skill '{skill_name}' not found or not enabled"}

    code = skill.get("code", "")
    if not code or code.startswith("#"):
        return {"error": f"Skill '{skill_name}' has no executable code"}

    # Execute skill code in a sandboxed namespace
    try:
        namespace = {}
        exec(code, namespace)

        execute_fn = namespace.get("execute")
        if not execute_fn:
            return {"error": f"Skill '{skill_name}' has no execute() function"}

        import asyncio
        if asyncio.iscoroutinefunction(execute_fn):
            result = await execute_fn(**args)
        else:
            result = execute_fn(**args)

        return {"result": result}
    except Exception as e:
        return {"error": f"Skill '{skill_name}' execution failed: {str(e)}"}


@router.post("/sessions/{session_id}/messages")
async def send_message(
    session_id: str,
    body: SendMessageRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a message and get a response with protocol execution support."""
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == uuid.UUID(session_id),
            ChatSession.user_id == user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    model_ids = body.model_ids or session.model_ids or []
    # Filter out agent: prefixed entries from model_ids (they're not real models)
    model_ids = [m for m in model_ids if not m.startswith("agent:")]
    if not model_ids:
        # Try to resolve from agent's configuration
        if session.agent_id and session.agent:
            agent = session.agent
            if agent.agent_models:
                model_ids = [str(am.model_config_id) for am in sorted(agent.agent_models, key=lambda x: x.priority)]
            elif agent.model_id:
                model_ids = [str(agent.model_id)]
    if not model_ids:
        raise HTTPException(status_code=400, detail="No models selected for this chat")

    # Save user message
    user_msg = ChatMessage(
        session_id=session.id,
        role="user",
        content=body.content,
    )
    db.add(user_msg)
    await db.flush()

    # ── Initialize thinking tracker (only for agent sessions) ──
    tracker = None
    is_agent_session = bool(session.agent_id and session.agent)
    if is_agent_session:
        tracker = ThinkingTracker(db, session.agent_id, session.id, body.content)
        await tracker.start()

    # Build generation params — agent's file settings are source of truth
    gen_params = GenerationParams(temperature=session.temperature)
    system_prompt = session.system_prompt
    agent_protocols = []
    agent_skills = []
    agent_beliefs = None
    llm_calls_count = 0
    _resolved_model_name = None

    try:
        if is_agent_session:
            agent = session.agent
            agent_name = agent.name

            # ── Step: Load agent config ──
            if tracker:
                tracker.start_step_timer()
            agent_config = read_agent_config(agent_name)
            base_system_prompt = agent_config.get("system_prompt", "")

            agent_settings = read_agent_settings(agent_name)
            if agent_settings:
                gen_params = GenerationParams(
                    temperature=agent_settings.get("temperature", session.temperature),
                    top_p=agent_settings.get("top_p", 0.9),
                    top_k=agent_settings.get("top_k", 40),
                    max_tokens=agent_settings.get("max_tokens", 2048),
                    num_ctx=agent_settings.get("num_ctx", 32768),
                    repeat_penalty=agent_settings.get("repeat_penalty", 1.1),
                    num_predict=agent_settings.get("num_predict", -1),
                    stop=agent_settings.get("stop") or None,
                    num_thread=agent_settings.get("num_thread", 8),
                    num_gpu=agent_settings.get("num_gpu", 1),
                )

            if tracker:
                await tracker.step(
                    "config_load", "Load agent configuration",
                    input_data={"agent_name": agent_name},
                    output_data={
                        "has_system_prompt": bool(base_system_prompt),
                        "system_prompt_length": len(base_system_prompt),
                        "gen_params": {
                            "temperature": gen_params.temperature,
                            "top_p": gen_params.top_p,
                            "top_k": gen_params.top_k,
                            "max_tokens": gen_params.max_tokens,
                            "num_ctx": gen_params.num_ctx,
                        },
                    },
                    duration_ms=tracker.elapsed_step_ms(),
                )

            # ── Step: Load protocols, skills, beliefs, aspirations ──
            if tracker:
                tracker.start_step_timer()
            agent_protocols = await _load_agent_protocols(agent, db)
            agent_skills = await _load_agent_skills(agent.id, db, agent=agent)
            agent_beliefs = read_beliefs(agent_name)
            from app.api.agent_aspirations import read_aspirations
            agent_aspirations = read_aspirations(agent_name)

            if tracker:
                await tracker.step(
                    "context_load", "Load protocols, skills, beliefs, aspirations",
                    output_data={
                        "protocols_count": len(agent_protocols),
                        "protocols": [p.get("name", "?") for p in agent_protocols],
                        "skills_count": len(agent_skills),
                        "skills": [s.get("name", "?") for s in agent_skills],
                        "has_beliefs": bool(agent_beliefs),
                        "has_aspirations": bool(agent_aspirations),
                    },
                    duration_ms=tracker.elapsed_step_ms(),
                )

            # Get current protocol state (todo list, active child protocol)
            protocol_state = session.protocol_state or {}
            current_todo = protocol_state.get("todo_list")
            active_child = protocol_state.get("active_child_protocol")

            # ── Step: Build system prompt ──
            if tracker:
                tracker.start_step_timer()
            if agent_protocols:
                if active_child:
                    child_proto = None
                    for p in agent_protocols:
                        if p["name"] == active_child or p["id"] == active_child:
                            child_proto = p
                            break
                    if child_proto:
                        system_prompt = build_agent_system_prompt(
                            base_system_prompt=base_system_prompt,
                            agent_name=agent_name,
                            protocols=[{**child_proto, "is_main": True}],
                            available_skills=agent_skills or None,
                            current_todo=current_todo,
                            beliefs=agent_beliefs,
                            aspirations=agent_aspirations,
                        )
                    else:
                        system_prompt = build_agent_system_prompt(
                            base_system_prompt=base_system_prompt,
                            agent_name=agent_name,
                            protocols=agent_protocols,
                            available_skills=agent_skills or None,
                            current_todo=current_todo,
                            beliefs=agent_beliefs,
                            aspirations=agent_aspirations,
                        )
                else:
                    system_prompt = build_agent_system_prompt(
                        base_system_prompt=base_system_prompt,
                        agent_name=agent_name,
                        protocols=agent_protocols,
                        available_skills=agent_skills or None,
                        current_todo=current_todo,
                        beliefs=agent_beliefs,
                        aspirations=agent_aspirations,
                    )
            else:
                system_prompt = system_prompt or base_system_prompt

            if tracker:
                await tracker.step(
                    "prompt_build", "Build system prompt",
                    input_data={
                        "active_child_protocol": active_child,
                        "has_todo": bool(current_todo),
                    },
                    output_data={
                        "system_prompt_length": len(system_prompt) if system_prompt else 0,
                        "system_prompt_preview": (system_prompt[:500] + "...") if system_prompt and len(system_prompt) > 500 else system_prompt,
                    },
                    duration_ms=tracker.elapsed_step_ms(),
                )

        # Build conversation history
        history = []
        if system_prompt:
            history.append({"role": "system", "content": system_prompt})

        for msg in session.messages:
            if msg.role != "system":
                history.append({"role": msg.role, "content": msg.content})
        history.append({"role": "user", "content": body.content})

        if tracker:
            await tracker.step(
                "history_build", "Build conversation history",
                output_data={
                    "history_messages": len(history),
                    "total_chars": sum(len(m["content"]) for m in history),
                },
            )

        start = time.monotonic()

        # ── Step: LLM inference ──
        if tracker:
            tracker.start_step_timer()

        if session.multi_model and len(model_ids) > 1:
            response_data = await _multi_model_chat(model_ids, history, gen_params, db)
            llm_calls_count = len(model_ids) + 1  # models + synthesis
            _resolved_model_name = response_data.get("model_name")
        else:
            model_id = model_ids[0]
            provider, base_url, model_name, api_key = await _resolve_model(model_id, db)
            _resolved_model_name = model_name
            try:
                llm_resp = await _chat_with_model(
                    provider, base_url, model_name, api_key,
                    history, gen_params,
                )
            except Exception as e:
                if tracker:
                    await tracker.step(
                        "llm_call", f"LLM call to {model_name}",
                        input_data={"model": model_name, "provider": provider, "history_len": len(history)},
                        status="error",
                        error_message=str(e),
                        duration_ms=tracker.elapsed_step_ms(),
                    )
                    await tracker.fail(f"Model error: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Model error: {str(e)}")

            llm_calls_count = 1
            response_data = {
                "content": llm_resp.content,
                "model_name": model_name,
                "model_responses": None,
                "total_tokens": llm_resp.total_tokens,
                "prompt_tokens": getattr(llm_resp, "prompt_tokens", 0),
                "completion_tokens": getattr(llm_resp, "completion_tokens", 0),
            }

        llm_duration_ms = int((time.monotonic() - start) * 1000)

        if tracker:
            await tracker.step(
                "llm_call", f"LLM inference ({_resolved_model_name})",
                input_data={
                    "model": _resolved_model_name,
                    "history_messages": len(history),
                    "multi_model": bool(session.multi_model and len(model_ids) > 1),
                },
                output_data={
                    "response_length": len(response_data["content"]),
                    "response_preview": response_data["content"][:500],
                    "total_tokens": response_data.get("total_tokens", 0),
                    "prompt_tokens": response_data.get("prompt_tokens", 0),
                    "completion_tokens": response_data.get("completion_tokens", 0),
                },
                duration_ms=llm_duration_ms,
            )

        elapsed_ms = llm_duration_ms

        # ── Protocol response parsing ──
        msg_metadata = {}
        llm_content = response_data["content"]

        if session.agent_id and agent_protocols:
            if tracker:
                tracker.start_step_timer()

            protocol_state = session.protocol_state or {}

            # 1. Parse todo list updates
            new_todo = parse_todo_list(llm_content)
            if new_todo:
                protocol_state["todo_list"] = new_todo
                msg_metadata["todo_list"] = new_todo

            # 2. Parse delegation
            delegate_to = parse_delegate(llm_content)
            if delegate_to:
                protocol_state["active_child_protocol"] = delegate_to
                msg_metadata["delegated_to"] = delegate_to

            # 3. Parse skill invocations
            skill_calls = parse_skill_invocations(llm_content)

            if tracker:
                await tracker.step(
                    "response_parse", "Parse LLM response (todo, delegation, skills)",
                    output_data={
                        "todo_found": bool(new_todo),
                        "delegation_found": bool(delegate_to),
                        "delegation_target": delegate_to,
                        "skill_calls_found": len(skill_calls) if skill_calls else 0,
                        "skill_calls": [c["skill_name"] for c in skill_calls] if skill_calls else [],
                    },
                    duration_ms=tracker.elapsed_step_ms(),
                )

            if skill_calls and agent_skills:
                # ── Step: Execute skills ──
                if tracker:
                    tracker.start_step_timer()

                skill_results = []
                for call in skill_calls:
                    result = await _execute_skill(call["skill_name"], call["args"], agent_skills)
                    skill_results.append({
                        "skill": call["skill_name"],
                        "args": call["args"],
                        "result": result,
                    })
                msg_metadata["skill_results"] = skill_results

                if tracker:
                    await tracker.step(
                        "skill_exec", f"Execute {len(skill_results)} skill(s)",
                        input_data={"skills": [c["skill_name"] for c in skill_calls]},
                        output_data={
                            "results": [
                                {"skill": sr["skill"], "has_error": "error" in sr["result"]}
                                for sr in skill_results
                            ],
                        },
                        duration_ms=tracker.elapsed_step_ms(),
                    )

                # ── Step: Follow-up LLM call with skill results ──
                skill_feedback = "\n\n".join(
                    f"**Skill `{sr['skill']}` result:**\n```json\n{json.dumps(sr['result'], ensure_ascii=False, indent=2)}\n```"
                    for sr in skill_results
                )
                follow_up_prompt = (
                    f"Skills have been executed. Here are the results:\n\n{skill_feedback}\n\n"
                    "Continue with your protocol steps based on these results."
                )
                history.append({"role": "assistant", "content": llm_content})
                history.append({"role": "user", "content": follow_up_prompt})

                try:
                    if tracker:
                        tracker.start_step_timer()

                    model_id = model_ids[0]
                    provider, base_url, model_name, api_key = await _resolve_model(model_id, db)
                    follow_resp = await _chat_with_model(
                        provider, base_url, model_name, api_key,
                        history, gen_params,
                    )
                    llm_calls_count += 1

                    response_data["content"] = llm_content + "\n\n---\n\n" + follow_resp.content
                    response_data["total_tokens"] = response_data.get("total_tokens", 0) + follow_resp.total_tokens
                    elapsed_ms = int((time.monotonic() - start) * 1000)

                    new_todo2 = parse_todo_list(follow_resp.content)
                    if new_todo2:
                        protocol_state["todo_list"] = new_todo2
                        msg_metadata["todo_list"] = new_todo2

                    if tracker:
                        await tracker.step(
                            "follow_up_call", f"Follow-up LLM call after skills ({model_name})",
                            input_data={"model": model_name, "skill_feedback_length": len(skill_feedback)},
                            output_data={
                                "response_length": len(follow_resp.content),
                                "response_preview": follow_resp.content[:500],
                                "tokens": follow_resp.total_tokens,
                            },
                            duration_ms=tracker.elapsed_step_ms(),
                        )
                except Exception as e:
                    if tracker:
                        await tracker.step(
                            "follow_up_call", "Follow-up LLM call after skills",
                            status="error",
                            error_message=str(e),
                            duration_ms=tracker.elapsed_step_ms() if tracker._step_start else 0,
                        )

            # Save protocol state to session
            if tracker:
                tracker.start_step_timer()
            session.protocol_state = protocol_state
            await db.flush()
            if tracker:
                await tracker.step(
                    "protocol_update", "Save protocol state",
                    output_data={
                        "has_todo": bool(protocol_state.get("todo_list")),
                        "active_child": protocol_state.get("active_child_protocol"),
                    },
                    duration_ms=tracker.elapsed_step_ms(),
                )

        # Save assistant message
        assistant_msg = ChatMessage(
            session_id=session.id,
            role="assistant",
            content=response_data["content"],
            model_name=response_data.get("model_name"),
            model_responses=response_data.get("model_responses"),
            total_tokens=response_data.get("total_tokens", 0),
            duration_ms=elapsed_ms,
            msg_metadata=msg_metadata or None,
        )
        db.add(assistant_msg)
        await db.flush()
        await db.refresh(assistant_msg)

        # ── Complete thinking log ──
        if tracker:
            await tracker.complete(
                response_data["content"],
                message_id=assistant_msg.id,
                model_name=_resolved_model_name,
                total_tokens=response_data.get("total_tokens", 0),
                prompt_tokens=response_data.get("prompt_tokens", 0),
                completion_tokens=response_data.get("completion_tokens", 0),
                llm_calls_count=llm_calls_count,
            )

        # Auto-title: if first user message, summarize to title
        if len(session.messages) <= 2:
            title = body.content[:60]
            if len(body.content) > 60:
                title += "…"
            session.title = title
            await db.flush()

        return _message_to_response(assistant_msg)

    except HTTPException:
        raise
    except Exception as e:
        if tracker:
            await tracker.fail(str(e))
        raise


async def _multi_model_chat(
    model_ids: list[str],
    history: list[dict],
    params: GenerationParams,
    db: AsyncSession,
) -> dict:
    """
    Multi-model mode: query all models in parallel, then synthesize.
    Like Grok's multi-model — each model answers, then a synthesizer combines.
    """
    # Resolve all models
    resolved = []
    for mid in model_ids:
        try:
            provider, base_url, model_name, api_key = await _resolve_model(mid, db)
            resolved.append((mid, provider, base_url, model_name, api_key))
        except Exception:
            continue

    if not resolved:
        raise HTTPException(status_code=400, detail="No valid models could be resolved")

    # Query all models in parallel
    async def query_one(provider, base_url, model_name, api_key):
        try:
            resp = await _chat_with_model(
                provider, base_url, model_name, api_key,
                history, params,
            )
            return {"model": model_name, "content": resp.content, "tokens": resp.total_tokens}
        except Exception as e:
            return {"model": model_name, "content": f"[Error: {str(e)}]", "tokens": 0, "error": True}

    tasks = [query_one(p, b, m, a) for (_, p, b, m, a) in resolved]
    results = await asyncio.gather(*tasks)

    model_responses = {}
    total_tokens = 0
    for r in results:
        model_responses[r["model"]] = r["content"]
        total_tokens += r.get("tokens", 0)

    # If only 1 model succeeded, return its response directly
    successful = [r for r in results if not r.get("error")]
    if len(successful) == 1:
        return {
            "content": successful[0]["content"],
            "model_name": successful[0]["model"],
            "model_responses": model_responses,
            "total_tokens": total_tokens,
        }

    # Synthesize responses using the first model
    if successful:
        synth_provider, synth_base_url, synth_model, synth_api_key = (
            resolved[0][1], resolved[0][2], resolved[0][3], resolved[0][4]
        )

        # Build synthesis prompt
        synthesis_parts = []
        for r in successful:
            synthesis_parts.append(f"=== Response from {r['model']} ===\n{r['content']}")

        synthesis_prompt = (
            "You are a synthesis assistant. Below are responses from multiple AI models to the same question. "
            "Analyze all responses, combine the best insights, resolve any contradictions, "
            "and produce a single comprehensive answer. Be concise but thorough.\n\n"
            + "\n\n".join(synthesis_parts)
            + "\n\n=== Your synthesized answer ==="
        )

        synth_history = [{"role": "user", "content": synthesis_prompt}]

        try:
            synth_resp = await _chat_with_model(
                synth_provider, synth_base_url, synth_model, synth_api_key,
                synth_history, params,
            )
            total_tokens += synth_resp.total_tokens

            return {
                "content": synth_resp.content,
                "model_name": f"multi({','.join(r['model'] for r in successful)})",
                "model_responses": model_responses,
                "total_tokens": total_tokens,
            }
        except Exception:
            # Fallback: return concatenated responses
            pass

    # Fallback: format all responses
    formatted = "\n\n".join(
        f"**{r['model']}:**\n{r['content']}" for r in results
    )
    return {
        "content": formatted,
        "model_name": "multi",
        "model_responses": model_responses,
        "total_tokens": total_tokens,
    }


# ── Auto-title ───────────────────────────────────────────

@router.post("/sessions/{session_id}/auto-title")
async def auto_title_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a title for the session based on its content."""
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == uuid.UUID(session_id),
            ChatSession.user_id == user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    msgs = session.messages[:4]  # First few messages
    if not msgs:
        return {"title": session.title}

    summary = "\n".join(f"{m.role}: {m.content[:200]}" for m in msgs)

    model_ids = session.model_ids or []
    if model_ids:
        try:
            provider, base_url, model_name, api_key = await _resolve_model(model_ids[0], db)
            prompt = [{"role": "user", "content": f"Generate a very short title (3-6 words) for this conversation:\n\n{summary}\n\nTitle:"}]
            resp = await _chat_with_model(provider, base_url, model_name, api_key, prompt, GenerationParams(temperature=0.3))
            new_title = resp.content.strip().strip('"').strip("'")[:100]
            session.title = new_title
            await db.flush()
            return {"title": new_title}
        except Exception:
            pass

    return {"title": session.title}
