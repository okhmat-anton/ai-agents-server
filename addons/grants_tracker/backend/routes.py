"""
Grants Tracker addon — backend routes.

Scrapes grants.gov API and custom sources for grant opportunities.
Stores items in MongoDB with deduplication, filtering, and deadline tracking.
"""

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, Query, Depends

from app.database import get_mongodb
from app.core.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/addons/grants_tracker",
    tags=["addon-grants-tracker"],
    dependencies=[Depends(get_current_user)],
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GRANTS_GOV_API = "https://www.grants.gov/grantsws/rest/opportunities/search"
GRANTS_GOV_DETAIL = "https://www.grants.gov/grantsws/rest/opportunity/details"

COLLECTION = "grants_items"
META_COLLECTION = "grants_meta"
RESOURCES_COLLECTION = "grants_resources"

HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
}

# Known grant categories for filtering
GRANT_CATEGORIES = [
    "Agriculture", "Arts", "Business and Commerce", "Community Development",
    "Consumer Protection", "Disaster Prevention and Relief", "Education",
    "Employment, Labor and Training", "Energy", "Environment",
    "Food and Nutrition", "Health", "Housing", "Humanities",
    "Information Technology", "Income Security and Social Services",
    "Law, Justice and Legal Services", "Natural Resources",
    "Regional Development", "Science and Technology",
    "Social Services and Income Security", "Transportation",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _strip_html(html: str) -> str:
    if not html:
        return ""
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text).strip()


def _parse_date(date_str: str) -> Optional[str]:
    """Try to parse various date formats to ISO."""
    if not date_str:
        return None
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%b %d, %Y"):
        try:
            return datetime.strptime(date_str, fmt).isoformat()
        except (ValueError, TypeError):
            continue
    return date_str


def _matches_keywords(text: str, keywords: list[str]) -> bool:
    if not keywords:
        return True
    text_lower = (text or "").lower()
    return any(kw.lower() in text_lower for kw in keywords if kw.strip())


# ---------------------------------------------------------------------------
# 1. GRANTS LIST & SEARCH
# ---------------------------------------------------------------------------

@router.get("/grants")
async def list_grants(
    category: Optional[str] = None,
    status: Optional[str] = None,
    keyword: Optional[str] = None,
    min_amount: Optional[float] = None,
    bookmarked: Optional[bool] = None,
    sort: str = "close_date",
    limit: int = Query(100, le=500),
    offset: int = 0,
):
    """List stored grants with optional filters."""
    db = get_mongodb()
    query = {}

    if category:
        query["category"] = {"$regex": category, "$options": "i"}
    if status:
        now = datetime.now(timezone.utc).isoformat()
        if status == "open":
            query["$or"] = [
                {"close_date": {"$gte": now}},
                {"close_date": None},
                {"close_date": ""},
            ]
        elif status == "closed":
            query["close_date"] = {"$lt": now}
    if keyword:
        query["$or"] = [
            {"title": {"$regex": keyword, "$options": "i"}},
            {"description": {"$regex": keyword, "$options": "i"}},
            {"agency": {"$regex": keyword, "$options": "i"}},
        ]
    if min_amount is not None:
        query["award_ceiling"] = {"$gte": min_amount}
    if bookmarked:
        query["bookmarked"] = True

    sort_field = sort if sort in ("close_date", "award_ceiling", "posted_date", "title") else "close_date"
    sort_dir = -1 if sort_field in ("award_ceiling", "posted_date") else 1

    cursor = db[COLLECTION].find(query).sort(sort_field, sort_dir).skip(offset).limit(limit)
    items = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        items.append(doc)

    total = await db[COLLECTION].count_documents(query)
    return {"items": items, "total": total}


@router.get("/grants/{grant_id}")
async def get_grant(grant_id: str):
    """Get a single grant by ID."""
    from bson import ObjectId
    db = get_mongodb()
    doc = await db[COLLECTION].find_one({"_id": ObjectId(grant_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Grant not found")
    doc["_id"] = str(doc["_id"])
    return doc


@router.patch("/grants/{grant_id}")
async def update_grant(grant_id: str, body: dict):
    """Update grant fields (bookmarked, notes, tags)."""
    from bson import ObjectId
    db = get_mongodb()
    allowed = {"bookmarked", "notes", "tags", "custom_category"}
    update = {k: v for k, v in body.items() if k in allowed}
    if not update:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db[COLLECTION].update_one({"_id": ObjectId(grant_id)}, {"$set": update})
    return {"ok": True}


# ---------------------------------------------------------------------------
# 2. SCRAPING — grants.gov API
# ---------------------------------------------------------------------------

@router.post("/grants/scrape")
async def scrape_grants(
    keyword: Optional[str] = None,
    category: Optional[str] = None,
    page_size: int = Query(100, le=250),
):
    """Scrape grants from grants.gov public API."""
    db = get_mongodb()
    scraped = 0
    updated = 0

    try:
        params = {
            "keyword": keyword or "",
            "oppStatuses": "forecasted|posted",
            "sortBy": "openDate|desc",
            "rows": page_size,
            "offset": 0,
        }
        if category:
            params["fundingCategories"] = category

        async with httpx.AsyncClient(timeout=60, headers=HTTP_HEADERS) as client:
            resp = await client.get(GRANTS_GOV_API, params=params)
            resp.raise_for_status()
            data = resp.json()

        opportunities = data.get("oppHits", [])

        for opp in opportunities:
            opp_id = str(opp.get("id", ""))
            if not opp_id:
                continue

            doc = {
                "source": "grants.gov",
                "source_id": opp_id,
                "opportunity_number": opp.get("number", ""),
                "title": opp.get("title", "").strip(),
                "description": _strip_html(opp.get("synopsis", "") or opp.get("description", "")),
                "agency": opp.get("agency", {}).get("name", "") if isinstance(opp.get("agency"), dict) else str(opp.get("agency", "")),
                "category": opp.get("fundingCategory", {}).get("name", "") if isinstance(opp.get("fundingCategory"), dict) else "",
                "instrument_type": opp.get("fundingInstrumentType", ""),
                "award_floor": opp.get("awardFloor", 0),
                "award_ceiling": opp.get("awardCeiling", 0),
                "estimated_funding": opp.get("estimatedFunding", 0),
                "posted_date": _parse_date(opp.get("openDate", "")),
                "close_date": _parse_date(opp.get("closeDate", "")),
                "archive_date": _parse_date(opp.get("archiveDate", "")),
                "eligible_applicants": opp.get("eligibleApplicants", ""),
                "url": f"https://www.grants.gov/search-results-detail/{opp_id}",
                "status": "open" if opp.get("oppStatus", "").lower() in ("posted", "forecasted") else "closed",
                "scraped_at": datetime.now(timezone.utc).isoformat(),
            }

            existing = await db[COLLECTION].find_one({"source_id": opp_id, "source": "grants.gov"})
            if existing:
                await db[COLLECTION].update_one(
                    {"_id": existing["_id"]},
                    {"$set": {**doc, "bookmarked": existing.get("bookmarked", False),
                              "notes": existing.get("notes", ""), "tags": existing.get("tags", [])}}
                )
                updated += 1
            else:
                doc["bookmarked"] = False
                doc["notes"] = ""
                doc["tags"] = []
                doc["created_at"] = datetime.now(timezone.utc).isoformat()
                await db[COLLECTION].insert_one(doc)
                scraped += 1

    except httpx.HTTPError as e:
        logger.error("grants.gov scrape failed: %s", e)
        raise HTTPException(status_code=502, detail=f"grants.gov API error: {e}")

    # Update meta
    await db[META_COLLECTION].update_one(
        {"key": "grants_gov"},
        {"$set": {"last_scrape": datetime.now(timezone.utc).isoformat(),
                  "count": await db[COLLECTION].count_documents({"source": "grants.gov"})}},
        upsert=True,
    )

    return {"scraped": scraped, "updated": updated, "source": "grants.gov"}


# ---------------------------------------------------------------------------
# 3. CUSTOM RESOURCES (user-added grant sources)
# ---------------------------------------------------------------------------

@router.get("/resources")
async def list_resources():
    """List custom grant search resources/sources."""
    db = get_mongodb()
    items = []
    async for doc in db[RESOURCES_COLLECTION].find().sort("created_at", -1):
        doc["_id"] = str(doc["_id"])
        items.append(doc)
    return {"items": items}


@router.post("/resources")
async def add_resource(body: dict):
    """Add a custom grant resource (URL, name, type)."""
    db = get_mongodb()
    name = body.get("name", "").strip()
    url = body.get("url", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Resource name is required")

    doc = {
        "name": name,
        "url": url,
        "resource_type": body.get("resource_type", "website"),
        "description": body.get("description", ""),
        "category": body.get("category", ""),
        "active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    result = await db[RESOURCES_COLLECTION].insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return doc


@router.delete("/resources/{resource_id}")
async def delete_resource(resource_id: str):
    """Delete a custom grant resource."""
    from bson import ObjectId
    db = get_mongodb()
    await db[RESOURCES_COLLECTION].delete_one({"_id": ObjectId(resource_id)})
    return {"ok": True}


# ---------------------------------------------------------------------------
# 4. CATEGORIES & STATS
# ---------------------------------------------------------------------------

@router.get("/categories")
async def get_categories():
    """Return list of known grant categories."""
    return {"items": GRANT_CATEGORIES}


@router.get("/stats")
async def get_stats():
    """Counts and summary info."""
    db = get_mongodb()
    total = await db[COLLECTION].count_documents({})
    bookmarked = await db[COLLECTION].count_documents({"bookmarked": True})

    now = datetime.now(timezone.utc).isoformat()
    open_grants = await db[COLLECTION].count_documents({
        "$or": [
            {"close_date": {"$gte": now}},
            {"close_date": None},
            {"close_date": ""},
        ]
    })

    # Upcoming deadlines (next 30 days)
    from datetime import timedelta
    deadline_cutoff = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    upcoming = await db[COLLECTION].count_documents({
        "close_date": {"$gte": now, "$lte": deadline_cutoff}
    })

    resources = await db[RESOURCES_COLLECTION].count_documents({})

    return {
        "total": total,
        "bookmarked": bookmarked,
        "open": open_grants,
        "upcoming_deadlines": upcoming,
        "resources": resources,
    }


@router.get("/scrape/status")
async def scrape_status():
    """Return last scrape info."""
    db = get_mongodb()
    meta = {}
    async for doc in db[META_COLLECTION].find():
        key = doc.get("key", "unknown")
        meta[key] = {
            "last_scrape": doc.get("last_scrape"),
            "count": doc.get("count", 0),
        }
    return meta


# ---------------------------------------------------------------------------
# 5. DEADLINES & CALENDAR
# ---------------------------------------------------------------------------

@router.get("/deadlines")
async def get_deadlines(days: int = Query(90, le=365)):
    """Get grants with upcoming deadlines."""
    db = get_mongodb()
    now = datetime.now(timezone.utc).isoformat()
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()

    cursor = db[COLLECTION].find({
        "close_date": {"$gte": now, "$lte": cutoff}
    }).sort("close_date", 1).limit(200)

    items = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        items.append(doc)
    return {"items": items, "days": days}


# ---------------------------------------------------------------------------
# 6. SCRAPE ALL & CLEAR
# ---------------------------------------------------------------------------

@router.post("/scrape-all")
async def scrape_all():
    """Run full scrape cycle."""
    result = await scrape_grants()
    return {"grants_gov": result}


@router.delete("/clear")
async def clear_all():
    """Remove all stored grant data."""
    db = get_mongodb()
    g = await db[COLLECTION].delete_many({})
    m = await db[META_COLLECTION].delete_many({})
    return {"deleted_grants": g.deleted_count, "deleted_meta": m.deleted_count}
