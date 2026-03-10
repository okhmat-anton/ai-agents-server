"""
Backup Scheduler — periodic auto-backup using asyncio.

Started/stopped from main.py lifespan.
Settings read from system_settings MongoDB collection.
"""
import asyncio
import logging
from typing import Optional

from app.database import get_mongodb
from app.services.backup_service import create_backup, enforce_max_backups

logger = logging.getLogger(__name__)

_scheduler_task: Optional[asyncio.Task] = None


async def _get_settings() -> dict:
    """Read backup settings from MongoDB."""
    db = get_mongodb()
    from app.mongodb.services import SystemSettingService
    svc = SystemSettingService(db)
    settings = {}
    for key in ("auto_backup_enabled", "backup_interval_hours", "max_backups"):
        doc = await svc.find_one({"key": key})
        if doc:
            settings[key] = doc.value
    return {
        "enabled": settings.get("auto_backup_enabled", "false") == "true",
        "interval_hours": int(settings.get("backup_interval_hours", "24")),
        "max_backups": int(settings.get("max_backups", "10")),
    }


async def _scheduler_loop():
    """Main scheduler loop — runs create_backup periodically."""
    logger.info("Backup scheduler started")
    while True:
        try:
            cfg = await _get_settings()
            if not cfg["enabled"]:
                # Check again in 60s
                await asyncio.sleep(60)
                continue

            interval_sec = cfg["interval_hours"] * 3600
            logger.info(
                "Auto-backup scheduled: every %dh, max %d backups",
                cfg["interval_hours"], cfg["max_backups"],
            )
            await asyncio.sleep(interval_sec)

            # Re-check if still enabled before running
            cfg = await _get_settings()
            if not cfg["enabled"]:
                continue

            db = get_mongodb()
            logger.info("Running scheduled auto-backup...")
            result = await create_backup(db, note="auto-backup")
            enforce_max_backups(cfg["max_backups"])
            logger.info(
                "Auto-backup complete: %s (%d docs)",
                result["filename"], result["documents_count"],
            )

        except asyncio.CancelledError:
            logger.info("Backup scheduler cancelled")
            break
        except Exception:
            logger.exception("Backup scheduler error, retrying in 60s")
            await asyncio.sleep(60)


async def start_scheduler():
    """Start the backup scheduler background task."""
    global _scheduler_task
    if _scheduler_task and not _scheduler_task.done():
        return
    _scheduler_task = asyncio.create_task(_scheduler_loop())
    logger.info("Backup scheduler task created")


async def stop_scheduler():
    """Stop the backup scheduler."""
    global _scheduler_task
    if _scheduler_task and not _scheduler_task.done():
        _scheduler_task.cancel()
        try:
            await _scheduler_task
        except asyncio.CancelledError:
            pass
    _scheduler_task = None
    logger.info("Backup scheduler stopped")


async def restart_scheduler():
    """Restart the scheduler (called when settings change)."""
    await stop_scheduler()
    await start_scheduler()
