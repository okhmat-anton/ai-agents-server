"""
Model role resolution service.

Fallback chain:
1. Model assigned to the requested role
2. Base model (role="base")
3. First available local Ollama model
4. First available API model (any provider)
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.model_role import ModelRoleAssignment
from app.models.model_config import ModelConfig
from app.config import get_settings
from app.services.log_service import syslog


async def resolve_model_for_role(db: AsyncSession, role: str) -> ModelConfig | None:
    """
    Resolve a ModelConfig for the given role using the fallback chain:
    1. Exact role assignment
    2. Base model
    3. First active local Ollama model
    4. First active API model
    """
    # 1. Try exact role
    model = await _get_model_by_role(db, role)
    if model and model.is_active:
        return model

    # 2. Try base model (unless already asking for base)
    if role != "base":
        base_model = await _get_model_by_role(db, "base")
        if base_model and base_model.is_active:
            await syslog(db, "info",
                         f"Role '{role}' not assigned, falling back to base model: {base_model.name}",
                         source="model_resolver")
            return base_model

    # 3. Try first active local Ollama model
    result = await db.execute(
        select(ModelConfig)
        .where(ModelConfig.provider == "ollama", ModelConfig.is_active == True)
        .order_by(ModelConfig.created_at)
        .limit(1)
    )
    ollama_model = result.scalar_one_or_none()
    if ollama_model:
        await syslog(db, "info",
                     f"No base model, falling back to local Ollama: {ollama_model.name}",
                     source="model_resolver")
        return ollama_model

    # 4. Try first available API model
    result = await db.execute(
        select(ModelConfig)
        .where(ModelConfig.provider != "ollama", ModelConfig.is_active == True)
        .order_by(ModelConfig.created_at)
        .limit(1)
    )
    api_model = result.scalar_one_or_none()
    if api_model:
        await syslog(db, "info",
                     f"No local model, falling back to API model: {api_model.name}",
                     source="model_resolver")
        return api_model

    await syslog(db, "warning", f"No model found for role '{role}' — all fallbacks exhausted",
                 source="model_resolver")
    return None


async def _get_model_by_role(db: AsyncSession, role: str) -> ModelConfig | None:
    """Get the ModelConfig assigned to a role."""
    result = await db.execute(
        select(ModelConfig)
        .join(ModelRoleAssignment, ModelRoleAssignment.model_config_id == ModelConfig.id)
        .where(ModelRoleAssignment.role == role)
    )
    return result.scalar_one_or_none()


async def get_all_role_assignments(db: AsyncSession) -> dict[str, str]:
    """Return dict of {role: model_config_id} for all assignments."""
    result = await db.execute(select(ModelRoleAssignment))
    return {a.role: str(a.model_config_id) for a in result.scalars().all()}
