"""
Backup API — endpoints for managing system backups.
"""
import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from app.database import get_mongodb
from app.core.dependencies import get_current_user
from app.mongodb.models.user import MongoUser
from app.services.backup_service import (
    list_backups,
    create_backup,
    restore_backup,
    delete_backup,
    enforce_max_backups,
    BACKUP_DIR,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/backups", tags=["backups"])


# --- Schemas ---

class BackupCreateRequest(BaseModel):
    note: str = ""


class BackupSettingsUpdate(BaseModel):
    auto_backup_enabled: Optional[bool] = None
    backup_interval_hours: Optional[int] = None
    max_backups: Optional[int] = None


# --- Helpers ---

async def _get_backup_settings(db: AsyncIOMotorDatabase) -> dict:
    """Get backup settings from system_settings collection."""
    from app.mongodb.services import SystemSettingService
    svc = SystemSettingService(db)
    settings = {}
    for key in ("auto_backup_enabled", "backup_interval_hours", "max_backups"):
        setting = await svc.find_one({"key": key})
        if setting:
            settings[key] = setting.value
    return {
        "auto_backup_enabled": settings.get("auto_backup_enabled", "false") == "true",
        "backup_interval_hours": int(settings.get("backup_interval_hours", "24")),
        "max_backups": int(settings.get("max_backups", "10")),
    }


async def _set_backup_setting(db: AsyncIOMotorDatabase, key: str, value: str):
    """Set a single backup setting."""
    from app.mongodb.services import SystemSettingService
    svc = SystemSettingService(db)
    existing = await svc.find_one({"key": key})
    if existing:
        await svc.update(existing.id, {"value": value})
    else:
        from app.mongodb.models.system_setting import MongoSystemSetting
        await svc.create(MongoSystemSetting(key=key, value=value))


# --- Endpoints ---

@router.get("")
async def get_backups(
    _user: MongoUser = Depends(get_current_user),
):
    """List all backups."""
    return list_backups()


@router.post("")
async def trigger_backup(
    body: BackupCreateRequest,
    background_tasks: BackgroundTasks,
    _user: MongoUser = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Create a new backup (runs in background)."""
    result = await create_backup(db, note=body.note)

    # Enforce max backups
    settings = await _get_backup_settings(db)
    enforce_max_backups(settings["max_backups"])

    return result


@router.get("/settings/current")
async def get_backup_settings(
    _user: MongoUser = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Get backup settings (auto-backup config)."""
    return await _get_backup_settings(db)


@router.put("/settings/current")
async def update_backup_settings(
    body: BackupSettingsUpdate,
    _user: MongoUser = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Update backup settings and restart scheduler if needed."""
    if body.auto_backup_enabled is not None:
        await _set_backup_setting(db, "auto_backup_enabled", str(body.auto_backup_enabled).lower())
    if body.backup_interval_hours is not None:
        if body.backup_interval_hours < 1:
            raise HTTPException(status_code=400, detail="Interval must be at least 1 hour")
        await _set_backup_setting(db, "backup_interval_hours", str(body.backup_interval_hours))
    if body.max_backups is not None:
        if body.max_backups < 1:
            raise HTTPException(status_code=400, detail="Max backups must be at least 1")
        await _set_backup_setting(db, "max_backups", str(body.max_backups))

    # Restart scheduler with new settings
    from app.services.backup_scheduler import restart_scheduler
    await restart_scheduler()

    updated = await _get_backup_settings(db)
    return updated


@router.delete("/{filename}")
async def remove_backup(
    filename: str,
    _user: MongoUser = Depends(get_current_user),
):
    """Delete a backup file."""
    if not delete_backup(filename):
        raise HTTPException(status_code=404, detail="Backup not found")
    return {"message": f"Backup {filename} deleted"}


@router.post("/{filename}/restore")
async def trigger_restore(
    filename: str,
    _user: MongoUser = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Restore system from a backup."""
    try:
        result = await restore_backup(db, filename)
        return result
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Backup not found")
    except Exception as e:
        logger.exception("Restore failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Restore failed: {str(e)}")


@router.get("/{filename}/download")
async def download_backup(
    filename: str,
    _user: MongoUser = Depends(get_current_user),
):
    """Download a backup file."""
    path = BACKUP_DIR / filename
    if not path.exists() or not filename.startswith("backup_"):
        raise HTTPException(status_code=404, detail="Backup not found")
    return FileResponse(
        path=str(path),
        media_type="application/gzip",
        filename=filename,
    )
