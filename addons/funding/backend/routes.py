"""
Funding & Investors addon — backend routes.

Tracks VC firms, angel investors, and SMB financing programs.
Stores data in MongoDB with tagging, filtering, and search.
"""

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
    prefix="/api/addons/funding",
    tags=["addon-funding"],
    dependencies=[Depends(get_current_user)],
)

# ---------------------------------------------------------------------------
# Collections
# ---------------------------------------------------------------------------

VC_COLLECTION = "funding_vc_firms"
INVESTORS_COLLECTION = "funding_investors"
SMB_COLLECTION = "funding_smb_programs"
META_COLLECTION = "funding_meta"

HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
}

# ---------------------------------------------------------------------------
# Known data — top VC firms, accelerators, SBA programs
# ---------------------------------------------------------------------------

TOP_VC_FIRMS = [
    {"name": "Sequoia Capital", "type": "vc", "stages": ["Seed", "Series A", "Series B", "Growth"],
     "sectors": ["Technology", "Healthcare", "Crypto"], "location": "Menlo Park, CA",
     "website": "https://www.sequoiacap.com", "aum": "85B", "notable_investments": "Apple, Google, Stripe, Airbnb"},
    {"name": "Andreessen Horowitz (a16z)", "type": "vc", "stages": ["Seed", "Series A", "Series B", "Growth"],
     "sectors": ["Technology", "Crypto", "Bio", "Games"], "location": "Menlo Park, CA",
     "website": "https://a16z.com", "aum": "42B", "notable_investments": "Facebook, Coinbase, GitHub, Slack"},
    {"name": "Accel", "type": "vc", "stages": ["Seed", "Series A", "Series B"],
     "sectors": ["SaaS", "Fintech", "Security"], "location": "Palo Alto, CA",
     "website": "https://www.accel.com", "aum": "17B", "notable_investments": "Facebook, Dropbox, Slack, CrowdStrike"},
    {"name": "Lightspeed Venture Partners", "type": "vc", "stages": ["Seed", "Series A", "Growth"],
     "sectors": ["Enterprise", "Consumer", "Health"], "location": "Menlo Park, CA",
     "website": "https://lsvp.com", "aum": "18B", "notable_investments": "Snap, Affirm, Nutanix"},
    {"name": "Benchmark", "type": "vc", "stages": ["Seed", "Series A"],
     "sectors": ["Technology", "Consumer", "Marketplace"], "location": "San Francisco, CA",
     "website": "https://www.benchmark.com", "aum": "4B", "notable_investments": "eBay, Twitter, Uber, Discord"},
    {"name": "Greylock Partners", "type": "vc", "stages": ["Seed", "Series A", "Series B"],
     "sectors": ["Enterprise", "Consumer", "AI"], "location": "Menlo Park, CA",
     "website": "https://greylock.com", "aum": "5B", "notable_investments": "LinkedIn, Airbnb, Discord, Figma"},
    {"name": "Founders Fund", "type": "vc", "stages": ["Seed", "Series A", "Growth"],
     "sectors": ["Deep Tech", "Space", "AI", "Bio"], "location": "San Francisco, CA",
     "website": "https://foundersfund.com", "aum": "12B", "notable_investments": "SpaceX, Palantir, Stripe"},
    {"name": "Kleiner Perkins", "type": "vc", "stages": ["Seed", "Series A", "Series B"],
     "sectors": ["Hardtech", "Fintech", "Digital Health"], "location": "Menlo Park, CA",
     "website": "https://www.kleinerperkins.com", "aum": "9B", "notable_investments": "Google, Amazon, Twitter, Doordash"},
    {"name": "General Catalyst", "type": "vc", "stages": ["Seed", "Series A", "Growth"],
     "sectors": ["AI", "Health", "Fintech"], "location": "Cambridge, MA",
     "website": "https://www.generalcatalyst.com", "aum": "25B", "notable_investments": "Stripe, Airbnb, Snap"},
    {"name": "NEA (New Enterprise Associates)", "type": "vc", "stages": ["Seed", "Series A", "Growth"],
     "sectors": ["Technology", "Healthcare"], "location": "Menlo Park, CA",
     "website": "https://www.nea.com", "aum": "25B", "notable_investments": "Salesforce, Coursera, Robinhood"},
    {"name": "Y Combinator", "type": "accelerator", "stages": ["Pre-Seed", "Seed"],
     "sectors": ["All sectors"], "location": "Mountain View, CA",
     "website": "https://www.ycombinator.com", "aum": "N/A", "notable_investments": "Airbnb, Stripe, DoorDash, Coinbase"},
    {"name": "Techstars", "type": "accelerator", "stages": ["Pre-Seed", "Seed"],
     "sectors": ["All sectors"], "location": "Boulder, CO",
     "website": "https://www.techstars.com", "aum": "N/A", "notable_investments": "DigitalOcean, SendGrid, Sphero"},
    {"name": "500 Global", "type": "accelerator", "stages": ["Pre-Seed", "Seed"],
     "sectors": ["All sectors"], "location": "San Francisco, CA",
     "website": "https://500.co", "aum": "2.8B", "notable_investments": "Canva, Grab, Talkdesk"},
    {"name": "Tiger Global", "type": "vc", "stages": ["Series B", "Growth", "Late Stage"],
     "sectors": ["Technology", "Internet", "Fintech"], "location": "New York, NY",
     "website": "https://www.tigerglobal.com", "aum": "100B+", "notable_investments": "Facebook, JD.com, Stripe"},
    {"name": "SoftBank Vision Fund", "type": "vc", "stages": ["Growth", "Late Stage"],
     "sectors": ["Technology", "AI", "Transportation"], "location": "Tokyo/London",
     "website": "https://visionfund.com", "aum": "100B", "notable_investments": "Uber, WeWork, ByteDance, DoorDash"},
]

SBA_PROGRAMS = [
    {"name": "SBA 7(a) Loan Program", "type": "loan", "max_amount": 5000000,
     "description": "The most common SBA loan program. Provides financial help for businesses with special requirements.",
     "eligible": "Small businesses", "url": "https://www.sba.gov/funding-programs/loans/7a-loans", "agency": "SBA"},
    {"name": "SBA 504 Loan Program", "type": "loan", "max_amount": 5500000,
     "description": "Long-term, fixed rate financing for major fixed assets like equipment or real estate.",
     "eligible": "Small businesses", "url": "https://www.sba.gov/funding-programs/loans/504-loans", "agency": "SBA"},
    {"name": "SBA Microloan Program", "type": "loan", "max_amount": 50000,
     "description": "Small loans up to $50,000 for small businesses and nonprofits.",
     "eligible": "Small businesses, nonprofits", "url": "https://www.sba.gov/funding-programs/loans/microloans", "agency": "SBA"},
    {"name": "SBIR (Small Business Innovation Research)", "type": "grant", "max_amount": 2000000,
     "description": "Federal grants for small businesses to engage in research and development with commercialization potential.",
     "eligible": "Small businesses (500 or fewer employees)", "url": "https://www.sbir.gov", "agency": "Multiple federal agencies"},
    {"name": "STTR (Small Business Technology Transfer)", "type": "grant", "max_amount": 2000000,
     "description": "Federal grants requiring partnerships between small businesses and research institutions.",
     "eligible": "Small businesses with research institution partner", "url": "https://www.sbir.gov/about/about-sttr", "agency": "Multiple federal agencies"},
    {"name": "SBA Community Advantage Loans", "type": "loan", "max_amount": 350000,
     "description": "Loans for businesses in underserved markets.",
     "eligible": "Businesses in underserved communities", "url": "https://www.sba.gov", "agency": "SBA"},
    {"name": "USDA Business & Industry Loan Program", "type": "loan", "max_amount": 25000000,
     "description": "Loan guarantees for rural businesses to improve, develop, or finance business and industry.",
     "eligible": "Rural businesses", "url": "https://www.rd.usda.gov/programs-services/business-programs", "agency": "USDA"},
    {"name": "EDA (Economic Development Administration) Grants", "type": "grant", "max_amount": 3000000,
     "description": "Grants to promote economic development and job creation in distressed communities.",
     "eligible": "Communities, nonprofits, universities", "url": "https://www.eda.gov", "agency": "EDA"},
]


# ---------------------------------------------------------------------------
# 1. VC FIRMS
# ---------------------------------------------------------------------------

@router.get("/vc")
async def list_vc_firms(
    stage: Optional[str] = None,
    sector: Optional[str] = None,
    search: Optional[str] = None,
    firm_type: Optional[str] = None,
    limit: int = Query(100, le=500),
):
    """List VC firms with filters."""
    db = get_mongodb()
    query = {}
    if stage:
        query["stages"] = {"$regex": stage, "$options": "i"}
    if sector:
        query["sectors"] = {"$regex": sector, "$options": "i"}
    if firm_type:
        query["type"] = firm_type
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"notable_investments": {"$regex": search, "$options": "i"}},
            {"location": {"$regex": search, "$options": "i"}},
        ]

    cursor = db[VC_COLLECTION].find(query).sort("name", 1).limit(limit)
    items = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        items.append(doc)

    total = await db[VC_COLLECTION].count_documents(query)
    return {"items": items, "total": total}


@router.post("/vc")
async def add_vc_firm(body: dict):
    """Add or update a VC firm manually."""
    db = get_mongodb()
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Firm name is required")

    doc = {
        "name": name,
        "type": body.get("type", "vc"),
        "stages": body.get("stages", []),
        "sectors": body.get("sectors", []),
        "location": body.get("location", ""),
        "website": body.get("website", ""),
        "aum": body.get("aum", ""),
        "notable_investments": body.get("notable_investments", ""),
        "description": body.get("description", ""),
        "contact_email": body.get("contact_email", ""),
        "notes": body.get("notes", ""),
        "bookmarked": body.get("bookmarked", False),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    existing = await db[VC_COLLECTION].find_one({"name": {"$regex": f"^{re.escape(name)}$", "$options": "i"}})
    if existing:
        await db[VC_COLLECTION].update_one({"_id": existing["_id"]}, {"$set": doc})
        doc["_id"] = str(existing["_id"])
    else:
        doc["created_at"] = datetime.now(timezone.utc).isoformat()
        result = await db[VC_COLLECTION].insert_one(doc)
        doc["_id"] = str(result.inserted_id)
    return doc


@router.delete("/vc/{firm_id}")
async def delete_vc_firm(firm_id: str):
    from bson import ObjectId
    db = get_mongodb()
    await db[VC_COLLECTION].delete_one({"_id": ObjectId(firm_id)})
    return {"ok": True}


@router.post("/vc/seed")
async def seed_vc_firms():
    """Seed database with known top VC firms."""
    db = get_mongodb()
    seeded = 0
    for firm in TOP_VC_FIRMS:
        existing = await db[VC_COLLECTION].find_one({"name": firm["name"]})
        if not existing:
            firm["bookmarked"] = False
            firm["notes"] = ""
            firm["created_at"] = datetime.now(timezone.utc).isoformat()
            firm["updated_at"] = datetime.now(timezone.utc).isoformat()
            await db[VC_COLLECTION].insert_one(firm)
            seeded += 1
    await db[META_COLLECTION].update_one(
        {"key": "vc_seed"},
        {"$set": {"last_scrape": datetime.now(timezone.utc).isoformat(),
                  "count": await db[VC_COLLECTION].count_documents({})}},
        upsert=True,
    )
    return {"seeded": seeded, "total": await db[VC_COLLECTION].count_documents({})}


# ---------------------------------------------------------------------------
# 2. INVESTORS (individual angels / venture partners)
# ---------------------------------------------------------------------------

@router.get("/investors")
async def list_investors(
    investor_type: Optional[str] = None,
    sector: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(100, le=500),
):
    """List investors with filters."""
    db = get_mongodb()
    query = {}
    if investor_type:
        query["investor_type"] = investor_type
    if sector:
        query["sectors"] = {"$regex": sector, "$options": "i"}
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"firm": {"$regex": search, "$options": "i"}},
            {"bio": {"$regex": search, "$options": "i"}},
        ]

    cursor = db[INVESTORS_COLLECTION].find(query).sort("name", 1).limit(limit)
    items = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        items.append(doc)

    total = await db[INVESTORS_COLLECTION].count_documents(query)
    return {"items": items, "total": total}


@router.post("/investors")
async def add_investor(body: dict):
    """Add an investor profile."""
    db = get_mongodb()
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Investor name is required")

    doc = {
        "name": name,
        "investor_type": body.get("investor_type", "angel"),
        "firm": body.get("firm", ""),
        "title": body.get("title", ""),
        "sectors": body.get("sectors", []),
        "stages": body.get("stages", []),
        "check_size_min": body.get("check_size_min"),
        "check_size_max": body.get("check_size_max"),
        "location": body.get("location", ""),
        "linkedin": body.get("linkedin", ""),
        "twitter": body.get("twitter", ""),
        "email": body.get("email", ""),
        "website": body.get("website", ""),
        "bio": body.get("bio", ""),
        "notable_investments": body.get("notable_investments", ""),
        "notes": body.get("notes", ""),
        "bookmarked": body.get("bookmarked", False),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    result = await db[INVESTORS_COLLECTION].insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return doc


@router.patch("/investors/{investor_id}")
async def update_investor(investor_id: str, body: dict):
    from bson import ObjectId
    db = get_mongodb()
    body["updated_at"] = datetime.now(timezone.utc).isoformat()
    body.pop("_id", None)
    await db[INVESTORS_COLLECTION].update_one({"_id": ObjectId(investor_id)}, {"$set": body})
    return {"ok": True}


@router.delete("/investors/{investor_id}")
async def delete_investor(investor_id: str):
    from bson import ObjectId
    db = get_mongodb()
    await db[INVESTORS_COLLECTION].delete_one({"_id": ObjectId(investor_id)})
    return {"ok": True}


# ---------------------------------------------------------------------------
# 3. SMB FINANCING PROGRAMS
# ---------------------------------------------------------------------------

@router.get("/smb")
async def list_smb_programs(
    program_type: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(100, le=500),
):
    """List SMB financing programs."""
    db = get_mongodb()
    query = {}
    if program_type:
        query["type"] = program_type
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
            {"agency": {"$regex": search, "$options": "i"}},
        ]

    cursor = db[SMB_COLLECTION].find(query).sort("name", 1).limit(limit)
    items = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        items.append(doc)
    total = await db[SMB_COLLECTION].count_documents(query)
    return {"items": items, "total": total}


@router.post("/smb/seed")
async def seed_smb_programs():
    """Seed database with known SBA and government programs."""
    db = get_mongodb()
    seeded = 0
    for prog in SBA_PROGRAMS:
        existing = await db[SMB_COLLECTION].find_one({"name": prog["name"]})
        if not existing:
            prog["bookmarked"] = False
            prog["notes"] = ""
            prog["created_at"] = datetime.now(timezone.utc).isoformat()
            await db[SMB_COLLECTION].insert_one(prog)
            seeded += 1
    await db[META_COLLECTION].update_one(
        {"key": "smb_seed"},
        {"$set": {"last_scrape": datetime.now(timezone.utc).isoformat(),
                  "count": await db[SMB_COLLECTION].count_documents({})}},
        upsert=True,
    )
    return {"seeded": seeded, "total": await db[SMB_COLLECTION].count_documents({})}


@router.post("/smb")
async def add_smb_program(body: dict):
    """Add a custom SMB financing program."""
    db = get_mongodb()
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Program name is required")

    doc = {
        "name": name,
        "type": body.get("type", "loan"),
        "max_amount": body.get("max_amount"),
        "description": body.get("description", ""),
        "eligible": body.get("eligible", ""),
        "url": body.get("url", ""),
        "agency": body.get("agency", ""),
        "notes": body.get("notes", ""),
        "bookmarked": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    result = await db[SMB_COLLECTION].insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return doc


@router.delete("/smb/{program_id}")
async def delete_smb_program(program_id: str):
    from bson import ObjectId
    db = get_mongodb()
    await db[SMB_COLLECTION].delete_one({"_id": ObjectId(program_id)})
    return {"ok": True}


# ---------------------------------------------------------------------------
# 4. STATS
# ---------------------------------------------------------------------------

@router.get("/stats")
async def get_stats():
    db = get_mongodb()
    vc = await db[VC_COLLECTION].count_documents({})
    investors = await db[INVESTORS_COLLECTION].count_documents({})
    smb = await db[SMB_COLLECTION].count_documents({})
    return {"vc_firms": vc, "investors": investors, "smb_programs": smb}


@router.get("/scrape/status")
async def scrape_status():
    db = get_mongodb()
    meta = {}
    async for doc in db[META_COLLECTION].find():
        key = doc.get("key", "unknown")
        meta[key] = {"last_scrape": doc.get("last_scrape"), "count": doc.get("count", 0)}
    return meta


# ---------------------------------------------------------------------------
# 5. SEED ALL & CLEAR
# ---------------------------------------------------------------------------

@router.post("/scrape-all")
async def scrape_all():
    """Seed both VC firms and SMB programs databases."""
    vc = await seed_vc_firms()
    smb = await seed_smb_programs()
    return {"vc": vc, "smb": smb}


@router.delete("/clear")
async def clear_all():
    db = get_mongodb()
    v = await db[VC_COLLECTION].delete_many({})
    i = await db[INVESTORS_COLLECTION].delete_many({})
    s = await db[SMB_COLLECTION].delete_many({})
    m = await db[META_COLLECTION].delete_many({})
    return {"deleted_vc": v.deleted_count, "deleted_investors": i.deleted_count,
            "deleted_smb": s.deleted_count, "deleted_meta": m.deleted_count}
