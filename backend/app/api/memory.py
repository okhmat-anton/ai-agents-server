from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timezone
from app.database import get_mongodb
from app.core.dependencies import get_current_user
from app.mongodb.models import MongoMemory, MongoMemoryLink
from app.mongodb.services import AgentService, MemoryService, MemoryLinkService
from app.schemas.memory import (
    MemoryCreate, MemoryUpdate, MemoryResponse,
    MemoryLinkCreate, MemoryLinkResponse, MemoryGraphResponse, MemoryStatsResponse,
    MemorySearchRequest,
)
from app.schemas.common import MessageResponse

router = APIRouter(prefix="/api/agents/{agent_id}/memory", tags=["memory"])


async def _get_agent(agent_id: UUID, db: AsyncIOMotorDatabase):
    agent = await AgentService(db).get_by_id(str(agent_id))
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


def _mem_to_dict(m) -> dict:
    return {
        "id": m.id, "agent_id": m.agent_id, "type": m.type,
        "title": m.title, "content": m.content, "source": m.source,
        "importance": m.importance, "tags": m.tags or [], "category": m.category,
        "task_id": m.task_id, "embedding_id": m.embedding_id,
        "access_count": m.access_count, "last_accessed": m.last_accessed,
        "is_pinned": m.is_pinned, "created_at": m.created_at, "updated_at": m.updated_at,
    }


def _link_to_dict(l) -> dict:
    return {
        "id": l.id, "agent_id": l.agent_id,
        "source_id": l.source_id, "target_id": l.target_id,
        "relation_type": l.relation_type, "strength": l.strength,
        "description": l.description, "created_by": l.created_by,
        "created_at": l.created_at,
    }


@router.get("", response_model=list[MemoryResponse])
async def list_memories(
    agent_id: UUID,
    type: str | None = Query(None),
    category: str | None = Query(None),
    tags: str | None = Query(None),
    source: str | None = Query(None),
    importance_min: float | None = Query(None),
    search: str | None = Query(None),
    sort_by: str = Query("created_at"),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    _user = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    await _get_agent(agent_id, db)
    svc = MemoryService(db)
    filt: dict = {"agent_id": str(agent_id)}
    if type:
        filt["type"] = type
    if category:
        filt["category"] = category
    if source:
        filt["source"] = source

    memories = await svc.get_all(filter=filt, skip=offset, limit=limit)

    if importance_min is not None:
        memories = [m for m in memories if m.importance >= importance_min]
    if search:
        sl = search.lower()
        memories = [m for m in memories if sl in m.content.lower() or sl in m.title.lower()]
    if tags:
        tag_list = [t.strip() for t in tags.split(",")]
        memories = [m for m in memories if m.tags and any(t in m.tags for t in tag_list)]

    reverse = True
    sort_key = sort_by if sort_by in ("created_at", "importance", "access_count") else "created_at"
    memories.sort(key=lambda m: getattr(m, sort_key, m.created_at) or m.created_at, reverse=reverse)
    return [_mem_to_dict(m) for m in memories]


@router.get("/stats", response_model=MemoryStatsResponse)
async def memory_stats(
    agent_id: UUID,
    _user = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    await _get_agent(agent_id, db)
    svc = MemoryService(db)
    total = await svc.count({"agent_id": str(agent_id)})
    all_mems = await svc.get_by_agent(str(agent_id), limit=10000)

    by_type: dict[str, int] = {}
    by_category: dict[str, int] = {}
    for m in all_mems:
        by_type[m.type] = by_type.get(m.type, 0) + 1
        by_category[m.category] = by_category.get(m.category, 0) + 1

    return MemoryStatsResponse(total=total, by_type=by_type, by_category=by_category)


@router.get("/tags")
async def memory_tags(
    agent_id: UUID,
    _user = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    await _get_agent(agent_id, db)
    all_mems = await MemoryService(db).get_by_agent(str(agent_id), limit=10000)
    tag_count: dict[str, int] = {}
    for m in all_mems:
        if m.tags:
            for tag in m.tags:
                tag_count[tag] = tag_count.get(tag, 0) + 1
    return [{"tag": k, "count": v} for k, v in sorted(tag_count.items(), key=lambda x: -x[1])]


@router.get("/{memory_id}", response_model=MemoryResponse)
async def get_memory(
    agent_id: UUID,
    memory_id: UUID,
    _user = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    await _get_agent(agent_id, db)
    svc = MemoryService(db)
    mem = await svc.get_by_id(str(memory_id))
    if not mem or mem.agent_id != str(agent_id):
        raise HTTPException(status_code=404, detail="Memory not found")
    updated = await svc.update(str(memory_id), {
        "access_count": mem.access_count + 1,
        "last_accessed": datetime.now(timezone.utc).isoformat(),
    })
    return _mem_to_dict(updated)


@router.post("", response_model=MemoryResponse, status_code=201)
async def create_memory(
    agent_id: UUID,
    body: MemoryCreate,
    _user = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    await _get_agent(agent_id, db)
    mem = MongoMemory(**body.model_dump(), agent_id=str(agent_id), source="user")
    created = await MemoryService(db).create(mem)
    return _mem_to_dict(created)


@router.put("/{memory_id}", response_model=MemoryResponse)
async def update_memory(
    agent_id: UUID,
    memory_id: UUID,
    body: MemoryUpdate,
    _user = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    await _get_agent(agent_id, db)
    svc = MemoryService(db)
    mem = await svc.get_by_id(str(memory_id))
    if not mem or mem.agent_id != str(agent_id):
        raise HTTPException(status_code=404, detail="Memory not found")
    update_data = body.model_dump(exclude_unset=True)
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    updated = await svc.update(str(memory_id), update_data)
    return _mem_to_dict(updated)


@router.delete("/{memory_id}", response_model=MessageResponse)
async def delete_memory(
    agent_id: UUID,
    memory_id: UUID,
    _user = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    await _get_agent(agent_id, db)
    svc = MemoryService(db)
    mem = await svc.get_by_id(str(memory_id))
    if not mem or mem.agent_id != str(agent_id):
        raise HTTPException(status_code=404, detail="Memory not found")
    await svc.delete(str(memory_id))
    return MessageResponse(message="Memory deleted")


@router.post("/{memory_id}/pin", response_model=MemoryResponse)
async def pin_memory(
    agent_id: UUID, memory_id: UUID,
    _user = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    await _get_agent(agent_id, db)
    svc = MemoryService(db)
    mem = await svc.get_by_id(str(memory_id))
    if not mem or mem.agent_id != str(agent_id):
        raise HTTPException(status_code=404, detail="Memory not found")
    updated = await svc.update(str(memory_id), {"is_pinned": True})
    return _mem_to_dict(updated)


@router.post("/{memory_id}/unpin", response_model=MemoryResponse)
async def unpin_memory(
    agent_id: UUID, memory_id: UUID,
    _user = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    await _get_agent(agent_id, db)
    svc = MemoryService(db)
    mem = await svc.get_by_id(str(memory_id))
    if not mem or mem.agent_id != str(agent_id):
        raise HTTPException(status_code=404, detail="Memory not found")
    updated = await svc.update(str(memory_id), {"is_pinned": False})
    return _mem_to_dict(updated)


@router.post("/search")
async def search_memory(
    agent_id: UUID,
    body: MemorySearchRequest,
    _user = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Semantic search placeholder — falls back to text search."""
    await _get_agent(agent_id, db)
    all_mems = await MemoryService(db).get_by_agent(str(agent_id), limit=10000)

    query_lower = body.query.lower()
    results = [m for m in all_mems if query_lower in m.content.lower() or query_lower in m.title.lower()]

    if body.tags:
        results = [m for m in results if m.tags and any(t in m.tags for t in body.tags)]
    if body.category:
        results = [m for m in results if m.category == body.category]
    if body.importance_min is not None:
        results = [m for m in results if m.importance >= body.importance_min]

    results.sort(key=lambda m: m.importance, reverse=True)
    return [_mem_to_dict(m) for m in results[:body.limit]]


@router.delete("/bulk", response_model=MessageResponse)
async def bulk_delete_memory(
    agent_id: UUID,
    ids: str | None = Query(None, description="Comma-separated UUIDs"),
    _user = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    await _get_agent(agent_id, db)
    if ids:
        svc = MemoryService(db)
        uuid_list = [i.strip() for i in ids.split(",")]
        for mid in uuid_list:
            await svc.delete(mid)
    return MessageResponse(message="Memories deleted")


# ------- Memory Links -------
@router.get("/{memory_id}/links", response_model=list[MemoryLinkResponse])
async def list_memory_links(
    agent_id: UUID,
    memory_id: UUID,
    type: str | None = Query(None),
    _user = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    await _get_agent(agent_id, db)
    all_links = await MemoryLinkService(db).get_by_agent(str(agent_id))
    mid = str(memory_id)
    links = [l for l in all_links if l.source_id == mid or l.target_id == mid]
    if type:
        links = [l for l in links if l.relation_type == type]
    return [_link_to_dict(l) for l in links]


@router.get("/graph", response_model=MemoryGraphResponse)
async def memory_graph(
    agent_id: UUID,
    type: str | None = Query(None),
    _user = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    await _get_agent(agent_id, db)
    aid = str(agent_id)

    memories = await MemoryService(db).get_by_agent(aid, limit=500)
    nodes = [
        {"id": m.id, "title": m.title, "type": m.type, "importance": m.importance, "tags": m.tags or []}
        for m in memories
    ]

    all_links = await MemoryLinkService(db).get_by_agent(aid)
    if type:
        types = [t.strip() for t in type.split(",")]
        all_links = [l for l in all_links if l.relation_type in types]
    edges = [
        {"id": l.id, "source": l.source_id, "target": l.target_id,
         "relation_type": l.relation_type, "strength": l.strength}
        for l in all_links
    ]

    return MemoryGraphResponse(nodes=nodes, edges=edges)


@router.post("/links", response_model=MemoryLinkResponse, status_code=201)
async def create_memory_link(
    agent_id: UUID,
    body: MemoryLinkCreate,
    _user = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    await _get_agent(agent_id, db)
    link = MongoMemoryLink(
        agent_id=str(agent_id),
        source_id=str(body.source_id),
        target_id=str(body.target_id),
        relation_type=body.relation_type,
        strength=body.strength,
        description=body.description,
        created_by="user",
    )
    created = await MemoryLinkService(db).create(link)
    return _link_to_dict(created)


@router.delete("/links/{link_id}", response_model=MessageResponse)
async def delete_memory_link(
    agent_id: UUID,
    link_id: UUID,
    _user = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    await _get_agent(agent_id, db)
    svc = MemoryLinkService(db)
    link = await svc.get_by_id(str(link_id))
    if not link or link.agent_id != str(agent_id):
        raise HTTPException(status_code=404, detail="Link not found")
    await svc.delete(str(link_id))
    return MessageResponse(message="Link deleted")
