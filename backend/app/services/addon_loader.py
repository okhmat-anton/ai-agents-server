"""
Addon loader — scans addons/ directory and registers backend routers + settings.
"""
import importlib
import json
import logging
import sys
from pathlib import Path

from fastapi import FastAPI

logger = logging.getLogger("addon_loader")

ADDONS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "addons"


def _discover_addons() -> list[dict]:
    """Scan addons/ for directories with manifest.json."""
    addons = []
    if not ADDONS_DIR.exists():
        return addons
    for addon_dir in sorted(ADDONS_DIR.iterdir()):
        manifest_path = addon_dir / "manifest.json"
        if addon_dir.is_dir() and manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifest["_dir"] = str(addon_dir)
                addons.append(manifest)
            except Exception as e:
                logger.warning("Failed to load addon manifest %s: %s", manifest_path, e)
    return addons


def register_addon_routers(app: FastAPI):
    """Import and register FastAPI routers from each addon's backend/routes.py."""
    addons = _discover_addons()
    for manifest in addons:
        addon_id = manifest.get("id", "unknown")
        addon_dir = Path(manifest["_dir"])
        routes_file = addon_dir / "backend" / "routes.py"
        if not routes_file.exists():
            logger.info("Addon '%s' has no backend/routes.py — skipping router", addon_id)
            continue
        try:
            # Add addon backend dir to sys.path so it can import
            backend_dir = str(addon_dir / "backend")
            if backend_dir not in sys.path:
                sys.path.insert(0, backend_dir)

            spec = importlib.util.spec_from_file_location(
                f"addon_{addon_id}_routes", str(routes_file)
            )
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)

            if hasattr(mod, "router"):
                app.include_router(mod.router)
                logger.info("Registered addon router: %s (prefix=%s)", addon_id,
                            getattr(mod.router, "prefix", "?"))
            else:
                logger.warning("Addon '%s' routes.py has no 'router' attribute", addon_id)
        except Exception as e:
            logger.error("Failed to load addon '%s' router: %s", addon_id, e, exc_info=True)


async def seed_addon_settings(db):
    """Seed system settings defined in addon manifests (if missing)."""
    from app.mongodb.services import SystemSettingService
    from app.mongodb.models import MongoSystemSetting

    setting_service = SystemSettingService(db)
    existing = await setting_service.get_all(skip=0, limit=5000)
    existing_keys = {s.key for s in existing}

    addons = _discover_addons()
    for manifest in addons:
        addon_id = manifest.get("id", "unknown")
        # Seed addon enabled flag
        enabled_key = f"addon_{addon_id}_enabled"
        # Hidden addons default to disabled — enable manually in DB if needed
        default_enabled = "false" if manifest.get("hidden", False) else "true"
        if enabled_key not in existing_keys:
            new_setting = MongoSystemSetting(
                key=enabled_key,
                value=default_enabled,
                description=f"Enable/disable the {manifest.get('name', addon_id)} addon",
            )
            await setting_service.create(new_setting)
            existing_keys.add(enabled_key)
            logger.info("Seeded addon enabled setting: %s", enabled_key)
        # Seed addon-specific settings
        for s in manifest.get("settings", []):
            key = s["key"]
            if key not in existing_keys:
                new_setting = MongoSystemSetting(
                    key=key,
                    value=s.get("default", ""),
                    description=s.get("description", f"Setting for addon {addon_id}"),
                )
                await setting_service.create(new_setting)
                logger.info("Seeded addon setting: %s", key)


async def seed_addon_protocols(db):
    """Create default protocols defined in addon protocol JSON files."""
    from app.mongodb.services import ThinkingProtocolService

    proto_service = ThinkingProtocolService(db)
    existing = await proto_service.get_all(skip=0, limit=5000)
    existing_names = {p.name for p in existing}

    addons = _discover_addons()
    for manifest in addons:
        addon_dir = Path(manifest["_dir"])
        protocols_dir = addon_dir / "protocols"
        if not protocols_dir.exists():
            continue
        for proto_file in protocols_dir.glob("*.json"):
            try:
                proto_data = json.loads(proto_file.read_text(encoding="utf-8"))
                name = proto_data.get("name", "")
                if name and name not in existing_names:
                    from app.mongodb.models import MongoThinkingProtocol
                    proto = MongoThinkingProtocol(**proto_data, is_default=True)
                    await proto_service.create(proto)
                    logger.info("Seeded addon protocol: %s", name)
            except Exception as e:
                logger.warning("Failed to load addon protocol %s: %s", proto_file, e)


async def seed_addon_skills(db):
    """Register addon skills into MongoDB so agents can discover them."""
    from app.mongodb.services import SkillService
    from app.mongodb.models import MongoSkill

    svc = SkillService(db)
    existing = await svc.get_all(skip=0, limit=10000)
    existing_names = {s.name for s in existing}

    addons = _discover_addons()
    for manifest in addons:
        addon_dir = Path(manifest["_dir"])
        skills_dir = addon_dir / "skills"
        if not skills_dir.exists():
            continue
        for skill_dir in sorted(skills_dir.iterdir()):
            manifest_file = skill_dir / "manifest.json"
            code_file = skill_dir / "main.py"
            if not skill_dir.is_dir() or not manifest_file.exists() or not code_file.exists():
                continue
            try:
                skill_manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
                skill_name = skill_manifest.get("name", "")
                code = code_file.read_text(encoding="utf-8")

                if skill_name in existing_names:
                    # Update code if changed
                    existing_skill = next((s for s in existing if s.name == skill_name), None)
                    if existing_skill and existing_skill.code != code:
                        await svc.update(existing_skill.id, {"code": code})
                        logger.info("Updated addon skill: %s", skill_name)
                    continue

                skill = MongoSkill(
                    name=skill_name,
                    display_name=skill_manifest.get("display_name", skill_name),
                    description=skill_manifest.get("description", ""),
                    description_for_agent=skill_manifest.get("description_for_agent", ""),
                    category=skill_manifest.get("category", "addon"),
                    code=code,
                    input_schema=skill_manifest.get("input_schema", {}),
                    is_system=True,
                    is_shared=True,
                )
                await svc.create(skill)
                logger.info("Created addon skill: %s", skill_name)
            except Exception as e:
                logger.warning("Failed to load addon skill %s: %s", skill_dir.name, e)


def get_addon_manifests() -> list[dict]:
    """Return list of addon manifests for the frontend registry API."""
    addons = _discover_addons()
    # Strip internal fields and enrich with skill details
    result = []
    for m in addons:
        clean = {k: v for k, v in m.items() if not k.startswith("_")}
        # Load detailed skill manifests
        addon_dir = Path(m["_dir"])
        skills_dir = addon_dir / "skills"
        skills_details = []
        if skills_dir.exists():
            for skill_dir in sorted(skills_dir.iterdir()):
                skill_manifest_file = skill_dir / "manifest.json"
                if skill_dir.is_dir() and skill_manifest_file.exists():
                    try:
                        sm = json.loads(skill_manifest_file.read_text(encoding="utf-8"))
                        skills_details.append({
                            "name": sm.get("name", skill_dir.name),
                            "display_name": sm.get("display_name", sm.get("name", skill_dir.name)),
                            "description": sm.get("description", ""),
                            "category": sm.get("category", ""),
                            "input_schema": sm.get("input_schema", {}),
                        })
                    except Exception:
                        pass
        clean["skills_details"] = skills_details
        result.append(clean)
    return result
