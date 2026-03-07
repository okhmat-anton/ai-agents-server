"""Telegram integration service — Telethon client management, auth flow, message handling."""
import asyncio
import logging
import os
import random
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
from telethon.tl.functions.messages import SetTypingRequest
from telethon.tl.types import SendMessageTypingAction

from app.config import get_settings

logger = logging.getLogger(__name__)

# ── Global client registry ───────────────────────────────────────────────
# messenger_id -> { client, agent_id, config, trusted_users, ... }
_active_clients: Dict[str, Dict[str, Any]] = {}

# Pending auth flows: messenger_id -> { client, phone_code_hash }
_pending_auth: Dict[str, Dict[str, Any]] = {}

# Session files directory
_SESSION_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data", "messengers", "sessions"
)
os.makedirs(_SESSION_DIR, exist_ok=True)


def _session_path(messenger_id: str) -> str:
    return os.path.join(_SESSION_DIR, messenger_id)


# ── Auth Flow ────────────────────────────────────────────────────────────

async def start_auth_flow(messenger_id: str, api_id: int, api_hash: str, phone: str) -> dict:
    """Start Telegram auth — send code to phone. Returns phone_code_hash."""
    session_file = _session_path(messenger_id)

    client = TelegramClient(session_file, api_id, api_hash)
    await client.connect()

    if await client.is_user_authorized():
        me = await client.get_me()
        _pending_auth.pop(messenger_id, None)
        return {
            "status": "already_authenticated",
            "username": me.username or "",
            "phone": me.phone or "",
            "first_name": me.first_name or "",
        }

    result = await client.send_code_request(phone)

    _pending_auth[messenger_id] = {
        "client": client,
        "phone": phone,
        "phone_code_hash": result.phone_code_hash,
    }

    return {
        "status": "code_sent",
        "phone_code_hash": result.phone_code_hash,
        "message": f"Verification code sent to {phone}",
    }


async def submit_auth_code(messenger_id: str, code: str, phone_code_hash: str = None) -> dict:
    """Submit the verification code."""
    pending = _pending_auth.get(messenger_id)
    if not pending:
        return {"status": "error", "message": "No pending auth flow. Call /auth/start first."}

    client = pending["client"]
    phone = pending["phone"]
    pch = phone_code_hash or pending.get("phone_code_hash", "")

    try:
        await client.sign_in(phone, code, phone_code_hash=pch)
        me = await client.get_me()
        _pending_auth.pop(messenger_id, None)
        return {
            "status": "authenticated",
            "username": me.username or "",
            "phone": me.phone or "",
            "first_name": me.first_name or "",
        }
    except SessionPasswordNeededError:
        # 2FA needed
        return {"status": "2fa_required", "message": "Two-factor authentication password required."}
    except PhoneCodeInvalidError:
        return {"status": "error", "message": "Invalid verification code."}
    except Exception as e:
        logger.error(f"Auth code error for {messenger_id}: {e}")
        return {"status": "error", "message": str(e)}


async def submit_2fa_password(messenger_id: str, password: str) -> dict:
    """Submit 2FA password."""
    pending = _pending_auth.get(messenger_id)
    if not pending:
        return {"status": "error", "message": "No pending auth flow."}

    client = pending["client"]
    try:
        await client.sign_in(password=password)
        me = await client.get_me()
        _pending_auth.pop(messenger_id, None)
        return {
            "status": "authenticated",
            "username": me.username or "",
            "phone": me.phone or "",
            "first_name": me.first_name or "",
        }
    except Exception as e:
        logger.error(f"2FA error for {messenger_id}: {e}")
        return {"status": "error", "message": str(e)}


# ── Listener Management ─────────────────────────────────────────────────

async def start_telegram_listener(
    messenger_id: str,
    agent_id: str,
    creds: dict,
    account_doc: dict,
):
    """Start a Telegram client and register message handlers."""
    if messenger_id in _active_clients:
        logger.info(f"Telegram listener already active for {messenger_id}")
        return

    api_id = int(creds["api_id"])
    api_hash = creds["api_hash"]
    session_file = _session_path(messenger_id)

    client = TelegramClient(session_file, api_id, api_hash)
    await client.connect()

    if not await client.is_user_authorized():
        raise RuntimeError("Client not authenticated. Complete auth flow first.")

    me = await client.get_me()
    logger.info(f"Telegram listener started for {messenger_id} as @{me.username}")

    # Config
    trusted_users = account_doc.get("trusted_users", [])
    public_permissions = account_doc.get("public_permissions", [])
    config = account_doc.get("config", {})
    delay_min = config.get("response_delay_min", 2)
    delay_max = config.get("response_delay_max", 8)
    typing_indicator = config.get("typing_indicator", True)
    humanize = config.get("humanize_responses", True)
    casual = config.get("casual_tone", True)
    respond_mentions = config.get("respond_to_mentions", True)
    respond_groups = config.get("respond_in_groups", False)
    max_daily = config.get("max_daily_messages", 100)

    # Store in registry
    _active_clients[messenger_id] = {
        "client": client,
        "agent_id": agent_id,
        "messenger_id": messenger_id,
        "me": me,
        "trusted_users": trusted_users,
        "public_permissions": public_permissions,
        "config": config,
        "daily_count": 0,
        "last_count_reset": datetime.now(timezone.utc).date(),
    }

    @client.on(events.NewMessage(incoming=True))
    async def on_new_message(event):
        """Handle incoming Telegram messages."""
        try:
            await _handle_incoming_message(
                event=event,
                messenger_id=messenger_id,
                agent_id=agent_id,
                client=client,
                me=me,
                trusted_users=trusted_users,
                public_permissions=public_permissions,
                delay_min=delay_min,
                delay_max=delay_max,
                typing_indicator=typing_indicator,
                humanize=humanize,
                casual=casual,
                respond_mentions=respond_mentions,
                respond_groups=respond_groups,
                max_daily=max_daily,
            )
        except Exception as e:
            logger.error(f"Error handling Telegram message for {messenger_id}: {e}", exc_info=True)

    # Start receiving
    asyncio.create_task(_run_client(client, messenger_id))


async def _run_client(client: TelegramClient, messenger_id: str):
    """Keep client running until disconnected."""
    try:
        await client.run_until_disconnected()
    except Exception as e:
        logger.error(f"Telegram client {messenger_id} disconnected: {e}")
    finally:
        _active_clients.pop(messenger_id, None)
        logger.info(f"Telegram listener stopped for {messenger_id}")


async def stop_telegram_client(messenger_id: str):
    """Stop and disconnect a Telegram client."""
    entry = _active_clients.pop(messenger_id, None)
    if entry and entry.get("client"):
        try:
            await entry["client"].disconnect()
        except Exception as e:
            logger.warning(f"Error disconnecting Telegram client {messenger_id}: {e}")

    # Also clean up pending auth
    pending = _pending_auth.pop(messenger_id, None)
    if pending and pending.get("client"):
        try:
            await pending["client"].disconnect()
        except Exception:
            pass


async def stop_all_clients():
    """Stop all active Telegram clients (for shutdown)."""
    for mid in list(_active_clients.keys()):
        await stop_telegram_client(mid)


def get_active_clients() -> Dict[str, Any]:
    """Return info about active clients."""
    return {
        mid: {
            "agent_id": entry["agent_id"],
            "username": entry["me"].username if entry.get("me") else "",
            "daily_count": entry.get("daily_count", 0),
        }
        for mid, entry in _active_clients.items()
    }


# ── Message Handler ──────────────────────────────────────────────────────

async def _handle_incoming_message(
    event,
    messenger_id: str,
    agent_id: str,
    client: TelegramClient,
    me,
    trusted_users: list,
    public_permissions: list,
    delay_min: int,
    delay_max: int,
    typing_indicator: bool,
    humanize: bool,
    casual: bool,
    respond_mentions: bool,
    respond_groups: bool,
    max_daily: int,
):
    """Process an incoming Telegram message."""
    from app.database import get_mongodb
    db = get_mongodb()

    sender = await event.get_sender()
    if not sender:
        return

    # Skip our own messages
    if sender.id == me.id:
        return

    is_group = event.is_group or event.is_channel
    is_private = event.is_private

    # In groups: only respond if mentioned or if configured
    if is_group and not respond_groups:
        # Check if mentioned
        if respond_mentions and me.username:
            if f"@{me.username}" not in (event.raw_text or ""):
                return
        else:
            return

    # Check daily limit
    entry = _active_clients.get(messenger_id)
    if entry:
        today = datetime.now(timezone.utc).date()
        if entry.get("last_count_reset") != today:
            entry["daily_count"] = 0
            entry["last_count_reset"] = today
        if entry["daily_count"] >= max_daily:
            logger.warning(f"Daily message limit reached for {messenger_id}")
            return

    # Determine if trusted user
    sender_username = f"@{sender.username}" if sender.username else ""
    sender_id_str = str(sender.id)
    is_trusted = (
        sender_username in trusted_users
        or sender_id_str in trusted_users
        or f"user_id:{sender.id}" in trusted_users
    )

    message_text = event.raw_text or ""
    if not message_text.strip():
        return

    # Log incoming message
    from app.mongodb.services import MessengerMessageService
    msg_svc = MessengerMessageService(db)
    incoming_msg = MongoMessengerMessage(
        messenger_id=messenger_id,
        agent_id=agent_id,
        platform_message_id=str(event.id),
        chat_id=str(event.chat_id),
        user_id=sender_id_str,
        username=sender.username or "",
        display_name=getattr(sender, 'first_name', '') or "",
        direction="incoming",
        content=message_text,
        is_command=is_trusted,
        is_trusted_user=is_trusted,
    )
    await msg_svc.create(incoming_msg)

    # Generate response via agent
    response_text = await _generate_agent_response(
        db=db,
        agent_id=agent_id,
        messenger_id=messenger_id,
        message_text=message_text,
        sender_username=sender.username or sender_id_str,
        is_trusted=is_trusted,
        public_permissions=public_permissions,
        humanize=humanize,
        casual=casual,
        chat_id=str(event.chat_id),
    )

    if not response_text:
        return

    # Simulate human behaviour: typing delay
    if typing_indicator:
        try:
            await client(SetTypingRequest(
                peer=event.chat_id,
                action=SendMessageTypingAction()
            ))
        except Exception:
            pass

    delay = random.uniform(delay_min, delay_max)
    await asyncio.sleep(delay)

    # Send response
    try:
        await event.reply(response_text)
    except Exception as e:
        logger.error(f"Error sending Telegram message: {e}")
        return

    # Log outgoing message
    outgoing_msg = MongoMessengerMessage(
        messenger_id=messenger_id,
        agent_id=agent_id,
        chat_id=str(event.chat_id),
        user_id=str(me.id),
        username=me.username or "",
        display_name=me.first_name or "",
        direction="outgoing",
        content=response_text,
        is_command=False,
        is_trusted_user=False,
        response_id=incoming_msg.id,
    )
    await msg_svc.create(outgoing_msg)

    # Update daily count
    if entry:
        entry["daily_count"] = entry.get("daily_count", 0) + 1

    # Update last_active_at
    from app.mongodb.services import MessengerAccountService
    acc_svc = MessengerAccountService(db)
    await acc_svc.update(messenger_id, {
        "last_active_at": datetime.now(timezone.utc).isoformat(),
    })


# Need import at module level for MongoMessengerMessage
from app.mongodb.models.messenger import MongoMessengerMessage


async def _generate_agent_response(
    db,
    agent_id: str,
    messenger_id: str,
    message_text: str,
    sender_username: str,
    is_trusted: bool,
    public_permissions: list,
    humanize: bool,
    casual: bool,
    chat_id: str,
) -> Optional[str]:
    """Call the agent's LLM to generate a response for a Telegram message."""
    from app.mongodb.services import AgentService, ModelConfigService, MessengerMessageService
    from app.llm.ollama import OllamaProvider
    from app.llm.openai_compatible import OpenAICompatibleProvider
    from app.llm.base import Message

    agent_svc = AgentService(db)
    agent = await agent_svc.get_by_id(agent_id)
    if not agent:
        logger.error(f"Agent {agent_id} not found for messenger response")
        return None

    # Resolve model
    settings = get_settings()
    model_id = agent.model_name
    provider_instance = None

    if model_id:
        mc_svc = ModelConfigService(db)
        # Try to find model config
        configs = await mc_svc.get_all()
        model_cfg = None
        for cfg in configs:
            if cfg.model_id == model_id or cfg.id == (agent.model_id or ""):
                model_cfg = cfg
                break

        if model_cfg:
            if model_cfg.provider == "ollama":
                provider_instance = OllamaProvider(
                    base_url=settings.OLLAMA_BASE_URL,
                    model=model_cfg.model_id,
                )
            elif model_cfg.provider in ("openai", "openai_compatible"):
                provider_instance = OpenAICompatibleProvider(
                    base_url=model_cfg.base_url or "https://api.openai.com/v1",
                    api_key=model_cfg.api_key or "",
                    model=model_cfg.model_id,
                )

    if not provider_instance:
        # Fallback: try first available ollama model
        provider_instance = OllamaProvider(
            base_url=settings.OLLAMA_BASE_URL,
            model=model_id or "llama3.2",
        )

    # Build system prompt
    system_parts = [agent.system_prompt] if agent.system_prompt else []

    if is_trusted:
        system_parts.append(
            f"\n[MESSENGER CONTEXT] "
            f"You are chatting in Telegram. The user @{sender_username} is a TRUSTED user. "
            f"You can execute commands and use all your skills. Respond helpfully."
        )
    else:
        perm_str = ", ".join(public_permissions) if public_permissions else "general conversation"
        human_note = ""
        if humanize:
            human_note = " Respond naturally, like a real human would — use casual language, occasional emoji. "
        if casual:
            human_note += " Keep it brief and conversational."
        system_parts.append(
            f"\n[MESSENGER CONTEXT] "
            f"You are chatting in Telegram as a regular person. "
            f"The user @{sender_username} is a regular user. "
            f"Your allowed capabilities: {perm_str}. "
            f"Do NOT reveal you are an AI agent. Do NOT execute privileged commands."
            f"{human_note}"
        )

    system_prompt = "\n".join(system_parts)

    # Get recent conversation context from this chat
    msg_svc = MessengerMessageService(db)
    recent = await msg_svc.get_by_chat(messenger_id, chat_id, limit=10)
    recent.reverse()  # oldest first

    messages = [Message(role="system", content=system_prompt)]
    for m in recent[:-1]:  # exclude the current message (already logged)
        role = "assistant" if m.direction == "outgoing" else "user"
        messages.append(Message(role=role, content=m.content))
    messages.append(Message(role="user", content=message_text))

    try:
        response = await provider_instance.chat(
            messages=messages,
            temperature=agent.temperature if humanize else 0.7,
            max_tokens=min(agent.max_tokens, 500),  # Keep telegram responses short
        )
        return response.content.strip() if response and response.content else None
    except Exception as e:
        logger.error(f"LLM error for messenger response: {e}")
        return None
