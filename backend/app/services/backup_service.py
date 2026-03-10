"""
Backup Service — creates and manages full MongoDB + files backups.

Backup format: tar.gz archive containing:
  - mongodb/ — JSON export of all MongoDB collections
  - chromadb/ — JSON export of all ChromaDB vector collections
  - data/ — copy of agents, skills, projects, audio, chat_media, logs dirs
  - metadata.json — backup metadata (timestamp, version, collections)
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import get_settings

logger = logging.getLogger(__name__)

BACKUP_DIR = Path("../data/backups")


def _get_backup_dir() -> Path:
    """Get (and create) the backups directory."""
    d = BACKUP_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def list_backups() -> list[dict]:
    """List all existing backups with metadata."""
    d = _get_backup_dir()
    backups = []
    for f in sorted(d.glob("backup_*.tar.gz"), reverse=True):
        meta = _read_backup_meta(f)
        backups.append({
            "filename": f.name,
            "path": str(f),
            "size_bytes": f.stat().st_size,
            "created_at": meta.get("created_at", ""),
            "collections": meta.get("collections", []),
            "version": meta.get("version", "unknown"),
            "documents_count": meta.get("documents_count", 0),
            "chromadb_collections": meta.get("chromadb_collections", 0),
        })
    return backups


def _read_backup_meta(archive_path: Path) -> dict:
    """Read metadata.json from a backup archive without full extraction."""
    try:
        with tarfile.open(archive_path, "r:gz") as tar:
            for member in tar.getmembers():
                if member.name.endswith("metadata.json"):
                    f = tar.extractfile(member)
                    if f:
                        return json.loads(f.read().decode("utf-8"))
    except Exception as e:
        logger.warning("Failed to read meta from %s: %s", archive_path.name, e)
    return {}


async def create_backup(db: AsyncIOMotorDatabase, note: str = "") -> dict:
    """
    Create a full backup:
      1. Export all MongoDB collections to JSON
      2. Copy data directories (agents, skills, projects)
      3. Package into tar.gz
    """
    settings = get_settings()
    backup_dir = _get_backup_dir()
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    archive_name = f"backup_{ts}.tar.gz"
    archive_path = backup_dir / archive_name

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        mongo_dir = tmp_path / "mongodb"
        mongo_dir.mkdir()
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        # 1. Export MongoDB collections
        collections = await db.list_collection_names()
        total_docs = 0
        collection_stats = []

        for coll_name in sorted(collections):
            if coll_name.startswith("system."):
                continue
            coll = db[coll_name]
            docs = []
            async for doc in coll.find({}):
                # Convert ObjectId and datetime for JSON serialization
                docs.append(_serialize_doc(doc))
            total_docs += len(docs)
            collection_stats.append({"name": coll_name, "count": len(docs)})

            coll_file = mongo_dir / f"{coll_name}.json"
            coll_file.write_text(
                json.dumps(docs, ensure_ascii=False, indent=None, default=str),
                encoding="utf-8",
            )
            logger.info("Exported %d docs from %s", len(docs), coll_name)

        # 2. Copy data directories
        dirs_to_copy = [
            (Path(settings.AGENTS_DIR), "agents"),
            (Path(settings.SKILLS_DIR), "skills"),
            (Path(settings.PROJECTS_DIR), "projects"),
            (Path("../data/skills"), "data_skills"),
            (Path("../data/audio"), "audio"),
            (Path("../data/chat_media"), "chat_media"),
            (Path("../data/logs"), "logs"),
        ]
        for src, name in dirs_to_copy:
            if src.exists():
                dst = data_dir / name
                shutil.copytree(src, dst, dirs_exist_ok=True)
                logger.info("Copied %s -> %s", src, dst)

        # 3. Export ChromaDB collections
        chroma_dir = tmp_path / "chromadb"
        chroma_dir.mkdir()
        chroma_collections_count = await _export_chromadb(settings.CHROMADB_URL, chroma_dir)

        # 4. Write metadata
        meta = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "version": settings.APP_VERSION,
            "collections": collection_stats,
            "documents_count": total_docs,
            "chromadb_collections": chroma_collections_count,
            "note": note,
            "data_dirs": [name for _, name in dirs_to_copy],
        }
        (tmp_path / "metadata.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # 5. Create tar.gz
        with tarfile.open(archive_path, "w:gz") as tar:
            for item in tmp_path.iterdir():
                tar.add(item, arcname=item.name)

    size = archive_path.stat().st_size
    logger.info("Backup created: %s (%d bytes, %d docs)", archive_name, size, total_docs)

    return {
        "filename": archive_name,
        "path": str(archive_path),
        "size_bytes": size,
        "created_at": meta["created_at"],
        "collections": collection_stats,
        "documents_count": total_docs,
        "version": meta["version"],
    }


async def restore_backup(db: AsyncIOMotorDatabase, filename: str) -> dict:
    """
    Restore a backup:
      1. Drop all existing collections
      2. Import MongoDB collections from JSON
      3. Restore data directories
    """
    settings = get_settings()
    backup_dir = _get_backup_dir()
    archive_path = backup_dir / filename

    if not archive_path.exists():
        raise FileNotFoundError(f"Backup not found: {filename}")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # Extract archive
        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(tmp_path)

        mongo_dir = tmp_path / "mongodb"
        data_dir = tmp_path / "data"

        # 1. Restore MongoDB collections
        restored_collections = []
        total_docs = 0

        if mongo_dir.exists():
            # Drop existing collections (except system)
            existing = await db.list_collection_names()
            for coll_name in existing:
                if not coll_name.startswith("system."):
                    await db.drop_collection(coll_name)

            for coll_file in sorted(mongo_dir.glob("*.json")):
                coll_name = coll_file.stem
                docs = json.loads(coll_file.read_text(encoding="utf-8"))
                if docs:
                    # Restore _id as-is (string UUIDs)
                    await db[coll_name].insert_many(docs)
                    total_docs += len(docs)
                restored_collections.append({"name": coll_name, "count": len(docs)})
                logger.info("Restored %d docs to %s", len(docs), coll_name)

        # 2. Restore ChromaDB collections
        chroma_dir = tmp_path / "chromadb"
        if chroma_dir.exists():
            await _import_chromadb(settings.CHROMADB_URL, chroma_dir)
            logger.info("ChromaDB collections restored")

        # 3. Restore data directories
        dirs_to_restore = [
            ("agents", Path(settings.AGENTS_DIR)),
            ("skills", Path(settings.SKILLS_DIR)),
            ("projects", Path(settings.PROJECTS_DIR)),
            ("data_skills", Path("../data/skills")),
            ("audio", Path("../data/audio")),
            ("chat_media", Path("../data/chat_media")),
            ("logs", Path("../data/logs")),
        ]
        restored_dirs = []
        if data_dir.exists():
            for name, dst in dirs_to_restore:
                src = data_dir / name
                if src.exists():
                    if dst.exists():
                        shutil.rmtree(dst)
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                    restored_dirs.append(name)
                    logger.info("Restored %s -> %s", src, dst)

    logger.info("Backup restored: %s (%d docs)", filename, total_docs)
    return {
        "filename": filename,
        "collections": restored_collections,
        "documents_count": total_docs,
        "data_dirs": restored_dirs,
    }


def delete_backup(filename: str) -> bool:
    """Delete a backup file."""
    backup_dir = _get_backup_dir()
    archive_path = backup_dir / filename
    if archive_path.exists() and archive_path.name.startswith("backup_"):
        archive_path.unlink()
        logger.info("Deleted backup: %s", filename)
        return True
    return False


def enforce_max_backups(max_count: int):
    """Delete oldest backups if count exceeds max_count."""
    if max_count <= 0:
        return
    d = _get_backup_dir()
    files = sorted(d.glob("backup_*.tar.gz"), key=lambda f: f.stat().st_mtime)
    while len(files) > max_count:
        oldest = files.pop(0)
        oldest.unlink()
        logger.info("Auto-deleted old backup: %s (max=%d)", oldest.name, max_count)


def _serialize_doc(doc: dict) -> dict:
    """Convert MongoDB doc to JSON-serializable dict."""
    from bson import ObjectId
    result = {}
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            result[k] = str(v)
        elif isinstance(v, datetime):
            result[k] = v.isoformat()
        elif isinstance(v, dict):
            result[k] = _serialize_doc(v)
        elif isinstance(v, list):
            result[k] = [
                _serialize_doc(i) if isinstance(i, dict)
                else str(i) if isinstance(i, ObjectId)
                else i.isoformat() if isinstance(i, datetime)
                else i
                for i in v
            ]
        else:
            result[k] = v
    return result


# --- ChromaDB helpers ---

async def _export_chromadb(chromadb_url: str, output_dir: Path) -> int:
    """Export all ChromaDB collections to JSON files. Returns count of exported collections."""
    exported = 0
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            # Try v2 API first, fall back to v1
            for api_prefix in ("/api/v2", "/api/v1"):
                r = await client.get(f"{chromadb_url}{api_prefix}/collections")
                if r.status_code == 200:
                    break
            else:
                logger.warning("ChromaDB not reachable, skipping vector backup")
                return 0

            collections = r.json()
            # v2 returns list of dicts, v1 also returns list of dicts
            if not collections:
                logger.info("No ChromaDB collections to export")
                return 0

            for coll in collections:
                coll_id = coll.get("id", "")
                coll_name = coll.get("name", "")
                if not coll_name:
                    continue

                # Get all items from collection
                get_url = f"{chromadb_url}{api_prefix}/collections/{coll_id}/get"
                r2 = await client.post(get_url, json={
                    "include": ["metadatas", "documents", "embeddings"],
                })
                if r2.status_code != 200:
                    logger.warning("Failed to export ChromaDB collection %s: %s", coll_name, r2.status_code)
                    continue

                data = r2.json()
                coll_data = {
                    "id": coll_id,
                    "name": coll_name,
                    "metadata": coll.get("metadata"),
                    "ids": data.get("ids", []),
                    "metadatas": data.get("metadatas", []),
                    "documents": data.get("documents", []),
                    "embeddings": data.get("embeddings", []),
                }

                out_file = output_dir / f"{coll_name}.json"
                out_file.write_text(
                    json.dumps(coll_data, ensure_ascii=False, default=str),
                    encoding="utf-8",
                )
                count = len(data.get("ids", []))
                logger.info("Exported ChromaDB collection %s (%d vectors)", coll_name, count)
                exported += 1

    except Exception as e:
        logger.warning("ChromaDB export failed (non-fatal): %s", e)
    return exported


async def _import_chromadb(chromadb_url: str, input_dir: Path):
    """Import ChromaDB collections from JSON files."""
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            # Detect API version
            api_prefix = "/api/v1"
            r = await client.get(f"{chromadb_url}/api/v2/heartbeat")
            if r.status_code == 200:
                api_prefix = "/api/v2"

            for coll_file in sorted(input_dir.glob("*.json")):
                coll_data = json.loads(coll_file.read_text(encoding="utf-8"))
                coll_name = coll_data.get("name", "")
                if not coll_name:
                    continue

                ids = coll_data.get("ids", [])
                if not ids:
                    continue

                # Delete existing collection if present
                await client.delete(f"{chromadb_url}{api_prefix}/collections/{coll_name}")

                # Create collection
                create_r = await client.post(
                    f"{chromadb_url}{api_prefix}/collections",
                    json={
                        "name": coll_name,
                        "metadata": coll_data.get("metadata") or {},
                        "get_or_create": True,
                    },
                )
                if create_r.status_code not in (200, 201):
                    logger.warning("Failed to create ChromaDB collection %s: %s", coll_name, create_r.text)
                    continue

                new_coll = create_r.json()
                new_coll_id = new_coll.get("id", "")

                # Add vectors in batches of 500
                batch_size = 500
                for i in range(0, len(ids), batch_size):
                    batch_ids = ids[i:i + batch_size]
                    payload = {"ids": batch_ids}
                    if coll_data.get("documents"):
                        payload["documents"] = coll_data["documents"][i:i + batch_size]
                    if coll_data.get("metadatas"):
                        payload["metadatas"] = coll_data["metadatas"][i:i + batch_size]
                    if coll_data.get("embeddings"):
                        payload["embeddings"] = coll_data["embeddings"][i:i + batch_size]

                    add_r = await client.post(
                        f"{chromadb_url}{api_prefix}/collections/{new_coll_id}/add",
                        json=payload,
                    )
                    if add_r.status_code not in (200, 201):
                        logger.warning("Failed to add batch to %s: %s", coll_name, add_r.text[:200])

                logger.info("Restored ChromaDB collection %s (%d vectors)", coll_name, len(ids))

    except Exception as e:
        logger.warning("ChromaDB import failed (non-fatal): %s", e)
