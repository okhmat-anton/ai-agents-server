"""
Model role resolution service.

Fallback chain:
1. Model assigned to the requested role
2. Base model (role="base")
3. First available local Ollama model
4. First available API model (any provider)
"""
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.mongodb.services import ModelConfigService, ModelRoleAssignmentService
from app.config import get_settings
from app.services.log_service import syslog


async def resolve_model_for_role(db: AsyncIOMotorDatabase, role: str):
    """
    Resolve a ModelConfig (MongoModelConfig) for the given role using the fallback chain:
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
            await syslog("info",
                         f"Role '{role}' not assigned, falling back to base model: {base_model.name}",
                         source="model_resolver")
            return base_model

    # 3. Try first active local Ollama model
    svc = ModelConfigService(db)
    all_models = await svc.get_all(filter={"provider": "ollama", "is_active": True}, limit=1)
    if all_models:
        ollama_model = all_models[0]
        await syslog("info",
                     f"No base model, falling back to local Ollama: {ollama_model.name}",
                     source="model_resolver")
        return ollama_model

    # 4. Try first available API model
    all_api = await svc.get_all(filter={"is_active": True}, limit=100)
    api_model = next((m for m in all_api if m.provider != "ollama"), None)
    if api_model:
        await syslog("info",
                     f"No local model, falling back to API model: {api_model.name}",
                     source="model_resolver")
        return api_model

    await syslog("warning", f"No model found for role '{role}' — all fallbacks exhausted",
                 source="model_resolver")
    return None


async def _get_model_by_role(db: AsyncIOMotorDatabase, role: str):
    """Get the ModelConfig assigned to a role."""
    mra_svc = ModelRoleAssignmentService(db)
    assignment = await mra_svc.find_one({"role": role})
    if not assignment:
        return None
    return await ModelConfigService(db).get_by_id(assignment.model_config_id)


async def get_all_role_assignments(db: AsyncIOMotorDatabase) -> dict[str, str]:
    """Return dict of {role: model_config_id} for all assignments."""
    mra_svc = ModelRoleAssignmentService(db)
    all_assignments = await mra_svc.get_all(limit=100)
    return {a.role: a.model_config_id for a in all_assignments}
