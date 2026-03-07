"""Messenger integration API — manage messenger accounts for agents."""
import logging
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from app.database import get_mongodb
from app.core.dependencies import get_current_user
from app.core.encryption import encrypt_dict, decrypt_dict
from app.mongodb.models.messenger import MongoMessengerAccount, MongoMessengerMessage
from app.mongodb.services import MessengerAccountService, MessengerMessageService, AgentService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agents/{agent_id}/messengers", tags=["messengers"])


# ── Schemas ──────────────────────────────────────────────────────────────

class MessengerCredentials(BaseModel):
    api_id: str = ""
    api_hash: str = ""
    phone: str = ""
    session_name: str = ""


class MessengerConfig(BaseModel):
    response_delay_min: int = 2
    response_delay_max: int = 8
    typing_indicator: bool = True
    humanize_responses: bool = True
    casual_tone: bool = True
    respond_to_mentions: bool = True
    respond_in_groups: bool = False
    max_daily_messages: int = 100
    autonomous_mode: bool = True


class MessengerCreate(BaseModel):
    platform: str = "telegram"
    name: str = ""
    credentials: MessengerCredentials = Field(default_factory=MessengerCredentials)
    trusted_users: List[str] = Field(default_factory=list)
    public_permissions: List[str] = Field(default_factory=lambda: ["answer_questions", "web_search"])
    config: MessengerConfig = Field(default_factory=MessengerConfig)


class MessengerUpdate(BaseModel):
    name: Optional[str] = None
    credentials: Optional[MessengerCredentials] = None
    trusted_users: Optional[List[str]] = None
    public_permissions: Optional[List[str]] = None
    config: Optional[MessengerConfig] = None
    is_active: Optional[bool] = None


class MessengerResponse(BaseModel):
    id: str
    agent_id: str
    platform: str
    name: str
    # credentials intentionally omitted for security — only partial info returned
    has_credentials: bool = False
    phone_masked: str = ""
    trusted_users: List[str] = []
    public_permissions: List[str] = []
    config: dict = {}
    is_active: bool = False
    is_authenticated: bool = False
    last_active_at: Optional[str] = None
    stats: dict = {}
    created_at: str
    updated_at: str


class AuthStartRequest(BaseModel):
    """Request body for starting Telegram authentication."""
    phone: Optional[str] = None  # override phone from credentials


class AuthCodeRequest(BaseModel):
    """Submit the verification code from Telegram."""
    code: str
    phone_code_hash: Optional[str] = None


class Auth2FARequest(BaseModel):
    """Submit 2FA password if enabled."""
    password: str


class MessengerStatsResponse(BaseModel):
    messages_today: int = 0
    messages_total: int = 0
    last_active_at: Optional[str] = None


class MessengerMessageResponse(BaseModel):
    id: str
    direction: str
    chat_id: str
    user_id: str
    username: str
    display_name: str
    content: str
    is_command: bool
    is_trusted_user: bool
    created_at: str


# ── Helpers ──────────────────────────────────────────────────────────────

def _mask_phone(phone: str) -> str:
    if not phone or len(phone) < 6:
        return "***"
    return phone[:3] + "*" * (len(phone) - 5) + phone[-2:]


def _build_response(acc: MongoMessengerAccount) -> dict:
    """Build safe response (no raw credentials)."""
    creds = acc.credentials or {}
    return MessengerResponse(
        id=acc.id,
        agent_id=acc.agent_id,
        platform=acc.platform,
        name=acc.name,
        has_credentials=bool(creds.get("api_id") and creds.get("api_hash")),
        phone_masked=_mask_phone(creds.get("phone", "")),
        trusted_users=acc.trusted_users,
        public_permissions=acc.public_permissions,
        config=acc.config,
        is_active=acc.is_active,
        is_authenticated=acc.is_authenticated,
        last_active_at=acc.last_active_at.isoformat() if acc.last_active_at else None,
        stats=acc.stats,
        created_at=acc.created_at.isoformat(),
        updated_at=acc.updated_at.isoformat(),
    ).model_dump()


# ── CRUD ─────────────────────────────────────────────────────────────────

@router.get("", response_model=list[dict])
async def list_messenger_accounts(
    agent_id: str,
    _user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """List all messenger accounts for an agent."""
    # Verify agent exists
    agent_svc = AgentService(db)
    agent = await agent_svc.get_by_id(agent_id)
    if not agent:
        raise HTTPException(404, "Agent not found")

    svc = MessengerAccountService(db)
    accounts = await svc.get_by_agent(agent_id)
    return [_build_response(a) for a in accounts]


@router.post("", status_code=201)
async def create_messenger_account(
    agent_id: str,
    body: MessengerCreate,
    _user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Create a new messenger account for an agent."""
    agent_svc = AgentService(db)
    agent = await agent_svc.get_by_id(agent_id)
    if not agent:
        raise HTTPException(404, "Agent not found")

    # Encrypt credentials before storing
    creds_plain = body.credentials.model_dump()
    encrypted_creds = encrypt_dict(creds_plain)

    account = MongoMessengerAccount(
        agent_id=agent_id,
        platform=body.platform,
        name=body.name or f"{body.platform}-{agent.name}",
        credentials=creds_plain,  # stored in memory; encrypted in DB
        trusted_users=body.trusted_users,
        public_permissions=body.public_permissions,
        config=body.config.model_dump(),
    )

    svc = MessengerAccountService(db)
    # Store with encrypted credentials
    doc = account.to_mongo()
    doc["credentials_encrypted"] = encrypted_creds
    doc["credentials"] = {}  # don't store raw
    await svc.collection.insert_one(doc)

    # Return with safe response
    return _build_response(account)


@router.get("/{messenger_id}")
async def get_messenger_account(
    agent_id: str,
    messenger_id: str,
    _user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Get a single messenger account."""
    svc = MessengerAccountService(db)
    acc = await svc.get_by_id(messenger_id)
    if not acc or acc.agent_id != agent_id:
        raise HTTPException(404, "Messenger account not found")
    return _build_response(acc)


@router.patch("/{messenger_id}")
async def update_messenger_account(
    agent_id: str,
    messenger_id: str,
    body: MessengerUpdate,
    _user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Update a messenger account."""
    svc = MessengerAccountService(db)
    acc = await svc.get_by_id(messenger_id)
    if not acc or acc.agent_id != agent_id:
        raise HTTPException(404, "Messenger account not found")

    update_data = {}
    if body.name is not None:
        update_data["name"] = body.name
    if body.trusted_users is not None:
        update_data["trusted_users"] = body.trusted_users
    if body.public_permissions is not None:
        update_data["public_permissions"] = body.public_permissions
    if body.config is not None:
        update_data["config"] = body.config.model_dump()
    if body.is_active is not None:
        update_data["is_active"] = body.is_active
    if body.credentials is not None:
        creds_plain = body.credentials.model_dump()
        update_data["credentials_encrypted"] = encrypt_dict(creds_plain)
        update_data["credentials"] = {}  # never store raw

    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

    updated = await svc.update(messenger_id, update_data)
    if not updated:
        raise HTTPException(404, "Messenger account not found")

    # Re-fetch to build proper response
    acc = await svc.get_by_id(messenger_id)
    # Decrypt creds to build response
    raw_doc = await svc.collection.find_one({"_id": messenger_id})
    if raw_doc and raw_doc.get("credentials_encrypted"):
        try:
            decrypted = decrypt_dict(raw_doc["credentials_encrypted"])
            acc.credentials = decrypted
        except Exception:
            pass

    return _build_response(acc)


@router.delete("/{messenger_id}")
async def delete_messenger_account(
    agent_id: str,
    messenger_id: str,
    _user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Delete a messenger account and its messages."""
    svc = MessengerAccountService(db)
    acc = await svc.get_by_id(messenger_id)
    if not acc or acc.agent_id != agent_id:
        raise HTTPException(404, "Messenger account not found")

    # Stop listener if running
    from app.services.telegram_service import stop_telegram_client
    await stop_telegram_client(messenger_id)

    # Delete messages
    msg_svc = MessengerMessageService(db)
    await msg_svc.collection.delete_many({"messenger_id": messenger_id})

    # Delete session file
    import os
    session_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "messengers", "sessions")
    for ext in ("", ".session"):
        path = os.path.join(session_dir, f"{messenger_id}{ext}")
        if os.path.exists(path):
            os.remove(path)

    # Delete account
    await svc.delete(messenger_id)
    return {"detail": "Messenger account deleted"}


# ── Telegram Auth Flow ───────────────────────────────────────────────────

@router.post("/{messenger_id}/auth/start")
async def start_telegram_auth(
    agent_id: str,
    messenger_id: str,
    body: AuthStartRequest = None,
    _user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Start Telegram authentication — sends code to phone."""
    svc = MessengerAccountService(db)
    raw_doc = await svc.collection.find_one({"_id": messenger_id})
    if not raw_doc or raw_doc.get("agent_id") != agent_id:
        raise HTTPException(404, "Messenger account not found")

    # Decrypt credentials
    encrypted = raw_doc.get("credentials_encrypted", "")
    if not encrypted:
        raise HTTPException(400, "No credentials stored. Update the account with API ID/Hash/Phone first.")

    try:
        creds = decrypt_dict(encrypted)
    except Exception:
        raise HTTPException(400, "Failed to decrypt credentials")

    api_id = creds.get("api_id")
    api_hash = creds.get("api_hash")
    phone = (body.phone if body and body.phone else creds.get("phone")) or ""

    if not api_id or not api_hash or not phone:
        raise HTTPException(400, "Missing api_id, api_hash or phone in credentials")

    from app.services.telegram_service import start_auth_flow
    result = await start_auth_flow(messenger_id, int(api_id), api_hash, phone)

    return result  # { "status": "code_sent", "phone_code_hash": "..." } or { "status": "already_authenticated" }


@router.post("/{messenger_id}/auth/code")
async def submit_telegram_code(
    agent_id: str,
    messenger_id: str,
    body: AuthCodeRequest,
    _user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Submit the verification code received via Telegram/SMS."""
    svc = MessengerAccountService(db)
    acc = await svc.get_by_id(messenger_id)
    if not acc or acc.agent_id != agent_id:
        raise HTTPException(404, "Messenger account not found")

    from app.services.telegram_service import submit_auth_code
    result = await submit_auth_code(messenger_id, body.code, body.phone_code_hash)

    if result.get("status") == "authenticated":
        # Mark as authenticated
        await svc.update(messenger_id, {
            "is_authenticated": True,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })

    return result


@router.post("/{messenger_id}/auth/2fa")
async def submit_telegram_2fa(
    agent_id: str,
    messenger_id: str,
    body: Auth2FARequest,
    _user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Submit 2FA password if account has two-step verification."""
    svc = MessengerAccountService(db)
    acc = await svc.get_by_id(messenger_id)
    if not acc or acc.agent_id != agent_id:
        raise HTTPException(404, "Messenger account not found")

    from app.services.telegram_service import submit_2fa_password
    result = await submit_2fa_password(messenger_id, body.password)

    if result.get("status") == "authenticated":
        await svc.update(messenger_id, {
            "is_authenticated": True,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })

    return result


# ── Start / Stop Listener ────────────────────────────────────────────────

@router.post("/{messenger_id}/start")
async def start_messenger_listener(
    agent_id: str,
    messenger_id: str,
    _user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Start listening for messages on this account."""
    svc = MessengerAccountService(db)
    raw_doc = await svc.collection.find_one({"_id": messenger_id})
    if not raw_doc or raw_doc.get("agent_id") != agent_id:
        raise HTTPException(404, "Messenger account not found")

    if not raw_doc.get("is_authenticated"):
        raise HTTPException(400, "Account not authenticated. Complete auth flow first.")

    encrypted = raw_doc.get("credentials_encrypted", "")
    if not encrypted:
        raise HTTPException(400, "No credentials stored")

    try:
        creds = decrypt_dict(encrypted)
    except Exception:
        raise HTTPException(400, "Failed to decrypt credentials")

    from app.services.telegram_service import start_telegram_listener
    await start_telegram_listener(messenger_id, agent_id, creds, raw_doc)

    await svc.update(messenger_id, {
        "is_active": True,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })

    return {"detail": "Listener started", "status": "active"}


@router.post("/{messenger_id}/stop")
async def stop_messenger_listener(
    agent_id: str,
    messenger_id: str,
    _user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Stop listening for messages on this account."""
    svc = MessengerAccountService(db)
    acc = await svc.get_by_id(messenger_id)
    if not acc or acc.agent_id != agent_id:
        raise HTTPException(404, "Messenger account not found")

    from app.services.telegram_service import stop_telegram_client
    await stop_telegram_client(messenger_id)

    await svc.update(messenger_id, {
        "is_active": False,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })

    return {"detail": "Listener stopped", "status": "stopped"}


# ── Stats & Messages ────────────────────────────────────────────────────

@router.get("/{messenger_id}/stats")
async def get_messenger_stats(
    agent_id: str,
    messenger_id: str,
    _user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Get messenger account statistics."""
    svc = MessengerAccountService(db)
    acc = await svc.get_by_id(messenger_id)
    if not acc or acc.agent_id != agent_id:
        raise HTTPException(404, "Messenger account not found")

    msg_svc = MessengerMessageService(db)
    today_count = await msg_svc.count_today(messenger_id)
    total = await msg_svc.count(filter={"messenger_id": messenger_id})

    return MessengerStatsResponse(
        messages_today=today_count,
        messages_total=total,
        last_active_at=acc.last_active_at.isoformat() if acc.last_active_at else None,
    ).model_dump()


@router.get("/{messenger_id}/messages", response_model=list[dict])
async def list_messenger_messages(
    agent_id: str,
    messenger_id: str,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    chat_id: Optional[str] = Query(None),
    _user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """List messages for a messenger account."""
    svc = MessengerAccountService(db)
    acc = await svc.get_by_id(messenger_id)
    if not acc or acc.agent_id != agent_id:
        raise HTTPException(404, "Messenger account not found")

    msg_svc = MessengerMessageService(db)
    if chat_id:
        messages = await msg_svc.get_by_chat(messenger_id, chat_id, limit=limit)
    else:
        messages = await msg_svc.get_by_messenger(messenger_id, limit=limit, skip=offset)

    return [
        MessengerMessageResponse(
            id=m.id,
            direction=m.direction,
            chat_id=m.chat_id,
            user_id=m.user_id,
            username=m.username,
            display_name=m.display_name,
            content=m.content[:500],  # truncate for list view
            is_command=m.is_command,
            is_trusted_user=m.is_trusted_user,
            created_at=m.created_at.isoformat(),
        ).model_dump()
        for m in messages
    ]
