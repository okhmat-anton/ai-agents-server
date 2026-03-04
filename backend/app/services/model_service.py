import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.model_config import ModelConfig
from app.config import get_settings


async def sync_ollama_models(db: AsyncSession):
    """Auto-detect Ollama models and add them to the database on startup."""
    settings = get_settings()
    base_url = settings.OLLAMA_BASE_URL

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{base_url}/api/tags")
            if resp.status_code != 200:
                print("[model_service] Ollama not available, skipping model sync")
                return
            data = resp.json()
    except Exception:
        print("[model_service] Ollama not reachable, skipping model sync")
        return

    ollama_models = data.get("models", [])
    if not ollama_models:
        print("[model_service] No Ollama models found")
        return

    # Get existing model_ids from DB
    result = await db.execute(
        select(ModelConfig.model_id).where(ModelConfig.provider == "ollama")
    )
    existing_model_ids = {row[0] for row in result.all()}

    added = 0
    for m in ollama_models:
        model_name = m.get("name", "")
        if not model_name or model_name in existing_model_ids:
            continue

        # Generate a friendly display name from model id
        display_name = model_name.split(":")[0].replace("-", " ").replace("/", " - ").title()
        size_gb = m.get("size", 0) / 1e9
        if size_gb > 0:
            display_name += f" ({size_gb:.1f}GB)"

        model_config = ModelConfig(
            name=display_name,
            model_id=model_name,
            provider="ollama",
            base_url=base_url,
            is_active=True,
        )
        db.add(model_config)
        added += 1

    if added:
        await db.commit()
        print(f"[model_service] Added {added} Ollama model(s) to database")
    else:
        print(f"[model_service] All {len(ollama_models)} Ollama model(s) already in database")
