import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.model_config import ModelConfig
from app.config import get_settings
from app.services.log_service import syslog


async def sync_ollama_models(db: AsyncSession):
    """Auto-detect Ollama models and add them to the database on startup."""
    settings = get_settings()
    base_url = settings.OLLAMA_BASE_URL

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{base_url}/api/tags")
            if resp.status_code != 200:
                await syslog(db, "warning", "Ollama not available, skipping model sync", source="system")
                return
            data = resp.json()
    except Exception:
        await syslog(db, "warning", "Ollama not reachable, skipping model sync", source="system")
        return

    ollama_models = data.get("models", [])
    if not ollama_models:
        await syslog(db, "info", "No Ollama models found", source="system")
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
        await syslog(db, "info", f"Synced {added} new Ollama model(s) to database", source="system",
                     metadata={"count": added})
    else:
        await syslog(db, "debug", f"All {len(ollama_models)} Ollama model(s) already in database", source="system")
