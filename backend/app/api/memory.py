from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from datetime import datetime, timezone
from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.agent import Agent
from app.models.memory import Memory, MemoryLink
from app.schemas.memory import (
    MemoryCreate, MemoryUpdate, MemoryResponse,
    MemoryLinkCreate, MemoryLinkResponse, MemoryGraphResponse, MemoryStatsResponse,
    MemorySearchRequest,
)
from app.schemas.common import MessageResponse

router = APIRouter(prefix="/api/agents/{agent_id}/memory", tags=["memory"])


async def _get_agent(agent_id: UUID, db: AsyncSession):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


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
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_agent(agent_id, db)
    q = select(Memory).where(Memory.agent_id == agent_id)
    if type:
        q = q.where(Memory.type == type)
    if category:
        q = q.where(Memory.category == category)
    if source:
        q = q.where(Memory.source == source)
    if importance_min is not None:
        q = q.where(Memory.importance >= importance_min)
    if search:
        q = q.where(Memory.content.ilike(f"%{search}%") | Memory.title.ilike(f"%{search}%"))
    if tags:
        tag_list = [t.strip() for t in tags.split(",")]
        q = q.where(Memory.tags.overlap(tag_list))

    order_col = getattr(Memory, sort_by, Memory.created_at)
    q = q.order_by(order_col.desc()).limit(limit).offset(offset)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/stats", response_model=MemoryStatsResponse)
async def memory_stats(
    agent_id: UUID,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_agent(agent_id, db)
    total = (await db.execute(select(func.count(Memory.id)).where(Memory.agent_id == agent_id))).scalar() or 0

    type_counts = await db.execute(
        select(Memory.type, func.count(Memory.id)).where(Memory.agent_id == agent_id).group_by(Memory.type)
    )
    by_type = {r[0]: r[1] for r in type_counts.all()}

    cat_counts = await db.execute(
        select(Memory.category, func.count(Memory.id)).where(Memory.agent_id == agent_id).group_by(Memory.category)
    )
    by_category = {r[0]: r[1] for r in cat_counts.all()}

    return MemoryStatsResponse(total=total, by_type=by_type, by_category=by_category)


@router.get("/tags")
async def memory_tags(
    agent_id: UUID,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_agent(agent_id, db)
    result = await db.execute(
        select(Memory.tags).where(Memory.agent_id == agent_id, Memory.tags.isnot(None))
    )
    tag_count: dict[str, int] = {}
    for row in result.scalars().all():
        if row:
            for tag in row:
                tag_count[tag] = tag_count.get(tag, 0) + 1
    return [{"tag": k, "count": v} for k, v in sorted(tag_count.items(), key=lambda x: -x[1])]


@router.get("/{memory_id}", response_model=MemoryResponse)
async def get_memory(
    agent_id: UUID,
    memory_id: UUID,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_agent(agent_id, db)
    result = await db.execute(select(Memory).where(Memory.id == memory_id, Memory.agent_id == agent_id))
    mem = result.scalar_one_or_none()
    if not mem:
        raise HTTPException(status_code=404, detail="Memory not found")
    mem.access_count += 1
    mem.last_accessed = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(mem)
    return mem


@router.post("", response_model=MemoryResponse, status_code=201)
async def create_memory(
    agent_id: UUID,
    body: MemoryCreate,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_agent(agent_id, db)
    mem = Memory(**body.model_dump(), agent_id=agent_id, source="user")
    db.add(mem)
    await db.flush()
    await db.refresh(mem)
    return mem


@router.put("/{memory_id}", response_model=MemoryResponse)
async def update_memory(
    agent_id: UUID,
    memory_id: UUID,
    body: MemoryUpdate,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_agent(agent_id, db)
    result = await db.execute(select(Memory).where(Memory.id == memory_id, Memory.agent_id == agent_id))
    mem = result.scalar_one_or_none()
    if not mem:
        raise HTTPException(status_code=404, detail="Memory not found")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(mem, key, value)
    await db.flush()
    await db.refresh(mem)
    return mem


@router.delete("/{memory_id}", response_model=MessageResponse)
async def delete_memory(
    agent_id: UUID,
    memory_id: UUID,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_agent(agent_id, db)
    result = await db.execute(select(Memory).where(Memory.id == memory_id, Memory.agent_id == agent_id))
    mem = result.scalar_one_or_none()
    if not mem:
        raise HTTPException(status_code=404, detail="Memory not found")
    await db.delete(mem)
    return MessageResponse(message="Memory deleted")


@router.post("/{memory_id}/pin", response_model=MemoryResponse)
async def pin_memory(
    agent_id: UUID, memory_id: UUID,
    _user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    await _get_agent(agent_id, db)
    result = await db.execute(select(Memory).where(Memory.id == memory_id, Memory.agent_id == agent_id))
    mem = result.scalar_one_or_none()
    if not mem:
        raise HTTPException(status_code=404, detail="Memory not found")
    mem.is_pinned = True
    await db.flush()
    await db.refresh(mem)
    return mem


@router.post("/{memory_id}/unpin", response_model=MemoryResponse)
async def unpin_memory(
    agent_id: UUID, memory_id: UUID,
    _user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    await _get_agent(agent_id, db)
    result = await db.execute(select(Memory).where(Memory.id == memory_id, Memory.agent_id == agent_id))
    mem = result.scalar_one_or_none()
    if not mem:
        raise HTTPException(status_code=404, detail="Memory not found")
    mem.is_pinned = False
    await db.flush()
    await db.refresh(mem)
    return mem


@router.post("/search")
async def search_memory(
    agent_id: UUID,
    body: MemorySearchRequest,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Semantic search placeholder — falls back to text search."""
    await _get_agent(agent_id, db)
    q = select(Memory).where(
        Memory.agent_id == agent_id,
        Memory.content.ilike(f"%{body.query}%") | Memory.title.ilike(f"%{body.query}%"),
    )
    if body.tags:
        q = q.where(Memory.tags.overlap(body.tags))
    if body.category:
        q = q.where(Memory.category == body.category)
    if body.importance_min is not None:
        q = q.where(Memory.importance >= body.importance_min)
    q = q.order_by(Memory.importance.desc()).limit(body.limit)
    result = await db.execute(q)
    return result.scalars().all()


@router.delete("/bulk", response_model=MessageResponse)
async def bulk_delete_memory(
    agent_id: UUID,
    ids: str | None = Query(None, description="Comma-separated UUIDs"),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_agent(agent_id, db)
    if ids:
        uuid_list = [UUID(i.strip()) for i in ids.split(",")]
        await db.execute(delete(Memory).where(Memory.agent_id == agent_id, Memory.id.in_(uuid_list)))
    return MessageResponse(message="Memories deleted")


# ------- Memory Links -------
@router.get("/{memory_id}/links", response_model=list[MemoryLinkResponse])
async def list_memory_links(
    agent_id: UUID,
    memory_id: UUID,
    type: str | None = Query(None),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_agent(agent_id, db)
    q = select(MemoryLink).where(
        MemoryLink.agent_id == agent_id,
        (MemoryLink.source_id == memory_id) | (MemoryLink.target_id == memory_id),
    )
    if type:
        q = q.where(MemoryLink.relation_type == type)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/graph", response_model=MemoryGraphResponse)
async def memory_graph(
    agent_id: UUID,
    type: str | None = Query(None),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_agent(agent_id, db)

    memories = await db.execute(select(Memory).where(Memory.agent_id == agent_id).limit(500))
    nodes = [
        {"id": str(m.id), "title": m.title, "type": m.type, "importance": m.importance, "tags": m.tags or []}
        for m in memories.scalars().all()
    ]

    q = select(MemoryLink).where(MemoryLink.agent_id == agent_id)
    if type:
        types = [t.strip() for t in type.split(",")]
        q = q.where(MemoryLink.relation_type.in_(types))
    links = await db.execute(q)
    edges = [
        {"id": str(l.id), "source": str(l.source_id), "target": str(l.target_id),
         "relation_type": l.relation_type, "strength": l.strength}
        for l in links.scalars().all()
    ]

    return MemoryGraphResponse(nodes=nodes, edges=edges)


@router.post("/links", response_model=MemoryLinkResponse, status_code=201)
async def create_memory_link(
    agent_id: UUID,
    body: MemoryLinkCreate,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_agent(agent_id, db)
    link = MemoryLink(
        agent_id=agent_id,
        source_id=body.source_id,
        target_id=body.target_id,
        relation_type=body.relation_type,
        strength=body.strength,
        description=body.description,
        created_by="user",
    )
    db.add(link)
    await db.flush()
    await db.refresh(link)
    return link


@router.delete("/links/{link_id}", response_model=MessageResponse)
async def delete_memory_link(
    agent_id: UUID,
    link_id: UUID,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_agent(agent_id, db)
    result = await db.execute(select(MemoryLink).where(MemoryLink.id == link_id, MemoryLink.agent_id == agent_id))
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    await db.delete(link)
    return MessageResponse(message="Link deleted")
