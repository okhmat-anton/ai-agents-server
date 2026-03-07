from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.database import get_db
from app.core.dependencies import get_current_user
from app.core.security import hash_password, verify_password, generate_api_key, hash_api_key
from app.models.user import User
from app.models.model_config import ModelConfig
from app.models.api_key import ApiKey
from app.models.system_setting import SystemSetting
from app.models.model_role import ModelRoleAssignment, MODEL_ROLES, MODEL_ROLE_LABELS
from app.schemas.auth import ChangePasswordRequest
from app.schemas.settings import (
    ModelConfigCreate, ModelConfigUpdate, ModelConfigResponse,
    ApiKeyCreate, ApiKeyResponse, ApiKeyCreatedResponse,
    SystemSettingResponse, SystemSettingUpdate,
    RoleAssignmentResponse, RoleAssignmentUpdate, RolesListResponse,
)
from app.schemas.common import MessageResponse

router = APIRouter(prefix="/api/settings", tags=["settings"])


# --- Password ---
@router.put("/password", response_model=MessageResponse)
async def change_password(
    body: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(body.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid old password")
    user.password_hash = hash_password(body.new_password)
    await db.flush()
    return MessageResponse(message="Password changed")


# --- Models ---
@router.get("/models", response_model=list[ModelConfigResponse])
async def list_models(
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ModelConfig).order_by(ModelConfig.created_at.desc()))
    return result.scalars().all()


@router.post("/models", response_model=ModelConfigResponse, status_code=201)
async def create_model(
    body: ModelConfigCreate,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    model = ModelConfig(**body.model_dump())
    db.add(model)
    await db.flush()
    await db.refresh(model)
    return model


@router.get("/models/{model_id}", response_model=ModelConfigResponse)
async def get_model(
    model_id: UUID,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ModelConfig).where(ModelConfig.id == model_id))
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return model


@router.put("/models/{model_id}", response_model=ModelConfigResponse)
async def update_model(
    model_id: UUID,
    body: ModelConfigUpdate,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ModelConfig).where(ModelConfig.id == model_id))
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(model, key, value)
    await db.flush()
    await db.refresh(model)
    return model


@router.delete("/models/{model_id}", response_model=MessageResponse)
async def delete_model(
    model_id: UUID,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ModelConfig).where(ModelConfig.id == model_id))
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    await db.delete(model)
    return MessageResponse(message="Model deleted")


@router.post("/models/{model_id}/test", response_model=MessageResponse)
async def test_model(
    model_id: UUID,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ModelConfig).where(ModelConfig.id == model_id))
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    from app.llm.ollama import OllamaProvider
    from app.llm.openai_compatible import OpenAICompatibleProvider

    try:
        if model.provider == "ollama":
            provider = OllamaProvider(model.base_url)
        else:
            provider = OpenAICompatibleProvider(model.base_url, model.api_key)
        connected = await provider.check_connection()
        if connected:
            return MessageResponse(message="Connection successful")
        raise HTTPException(status_code=400, detail="Connection failed")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Connection failed: {str(e)}")


@router.get("/models/{model_id}/available")
async def list_available_models(
    model_id: UUID,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ModelConfig).where(ModelConfig.id == model_id))
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    from app.llm.ollama import OllamaProvider
    from app.llm.openai_compatible import OpenAICompatibleProvider

    try:
        if model.provider == "ollama":
            provider = OllamaProvider(model.base_url)
        else:
            provider = OpenAICompatibleProvider(model.base_url, model.api_key)
        models = await provider.list_models()
        return {"models": models}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# --- Model Roles ---
@router.get("/model-roles/available")
async def get_available_roles(
    _user: User = Depends(get_current_user),
):
    """Return the list of all available roles with labels."""
    return [{"role": r, "label": MODEL_ROLE_LABELS.get(r, r)} for r in MODEL_ROLES]


@router.get("/model-roles", response_model=RolesListResponse)
async def get_model_roles(
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return all current role->model assignments."""
    result = await db.execute(
        select(ModelRoleAssignment).order_by(ModelRoleAssignment.role)
    )
    assignments = result.scalars().all()
    return RolesListResponse(
        assignments=[RoleAssignmentResponse(
            role=a.role,
            label=MODEL_ROLE_LABELS.get(a.role, a.role),
            model_config_id=a.model_config_id,
        ) for a in assignments],
        available_roles=[{"role": r, "label": MODEL_ROLE_LABELS.get(r, r)} for r in MODEL_ROLES],
    )


@router.put("/model-roles", response_model=RolesListResponse)
async def update_model_roles(
    body: RoleAssignmentUpdate,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Bulk update role assignments. Expects {assignments: [{role, model_config_id}]}."""
    # Validate roles
    for a in body.assignments:
        if a.role not in MODEL_ROLES:
            raise HTTPException(status_code=400, detail=f"Unknown role: {a.role}")

    # Delete all existing assignments
    await db.execute(delete(ModelRoleAssignment))

    # Insert new
    for a in body.assignments:
        db.add(ModelRoleAssignment(role=a.role, model_config_id=a.model_config_id))
    await db.flush()

    # Return updated list
    result = await db.execute(
        select(ModelRoleAssignment).order_by(ModelRoleAssignment.role)
    )
    assignments = result.scalars().all()
    return RolesListResponse(
        assignments=[RoleAssignmentResponse(
            role=a.role,
            label=MODEL_ROLE_LABELS.get(a.role, a.role),
            model_config_id=a.model_config_id,
        ) for a in assignments],
        available_roles=[{"role": r, "label": MODEL_ROLE_LABELS.get(r, r)} for r in MODEL_ROLES],
    )


# --- API Keys ---
@router.get("/api-keys", response_model=list[ApiKeyResponse])
async def list_api_keys(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ApiKey).where(ApiKey.user_id == user.id).order_by(ApiKey.created_at.desc()))
    return result.scalars().all()


@router.post("/api-keys", response_model=ApiKeyCreatedResponse, status_code=201)
async def create_api_key(
    body: ApiKeyCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    raw_key = generate_api_key()
    api_key = ApiKey(
        user_id=user.id,
        name=body.name,
        description=body.description,
        key_hash=hash_api_key(raw_key),
        key_prefix=raw_key[:8],
    )
    db.add(api_key)
    await db.flush()
    await db.refresh(api_key)
    return ApiKeyCreatedResponse(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        description=api_key.description,
        last_used_at=api_key.last_used_at,
        created_at=api_key.created_at,
        key=raw_key,
    )


@router.delete("/api-keys/{key_id}", response_model=MessageResponse)
async def delete_api_key(
    key_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user.id))
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    await db.delete(api_key)
    return MessageResponse(message="API key deleted")


# --- System Settings ---

# Default settings seeded on first access
_DEFAULT_SETTINGS = {
    "filesystem_access_enabled": {"value": "false", "description": "Allow full filesystem access (read/write/delete files on host)"},
    "system_access_enabled": {"value": "false", "description": "Allow terminal commands, process management and full system control"},
    "log_retention_days": {"value": "14", "description": "Number of days to retain logs (system, agent, thinking). Older logs are automatically deleted."},
}


async def _ensure_defaults(db: AsyncSession):
    """Seed default system settings if missing."""
    result = await db.execute(select(SystemSetting))
    existing = {s.key for s in result.scalars().all()}
    for key, cfg in _DEFAULT_SETTINGS.items():
        if key not in existing:
            db.add(SystemSetting(key=key, value=cfg["value"], description=cfg.get("description")))
    await db.flush()


async def get_setting_value(db: AsyncSession, key: str) -> str | None:
    """Helper to read a single setting value."""
    await _ensure_defaults(db)
    result = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
    setting = result.scalar_one_or_none()
    return setting.value if setting else None


@router.get("/system", response_model=list[SystemSettingResponse])
async def list_system_settings(
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _ensure_defaults(db)
    result = await db.execute(select(SystemSetting).order_by(SystemSetting.key))
    return result.scalars().all()


@router.put("/system/{key}", response_model=SystemSettingResponse)
async def update_system_setting(
    key: str,
    body: SystemSettingUpdate,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _ensure_defaults(db)
    result = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
    setting = result.scalar_one_or_none()
    if not setting:
        raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")
    setting.value = body.value
    await db.flush()
    await db.refresh(setting)
    return setting
