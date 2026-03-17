"""
US & Canada Finance addon — backend routes.

Tabs: News, Real Estate, Property Valuation, Property Search, Oil, Taxation, Programs.
Scrapes public data sources, stores in MongoDB, provides LLM-powered valuation analysis.
"""

import asyncio
import hashlib
import logging
import re
from datetime import datetime, timezone
from typing import Optional, List

import httpx
from fastapi import APIRouter, HTTPException, Query, Depends, Body
from pydantic import BaseModel

from app.database import get_mongodb
from app.core.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/addons/us_finance",
    tags=["addon-us-finance"],
    dependencies=[Depends(get_current_user)],
)

# ---------------------------------------------------------------------------
# Collections
# ---------------------------------------------------------------------------

COL_NEWS = "usf_news"
COL_REAL_ESTATE = "usf_real_estate"
COL_VALUATIONS = "usf_valuations"
COL_PROPERTY_SEARCH = "usf_property_search"
COL_AUCTION_ITEMS = "usf_auction_items"
COL_OIL = "usf_oil"
COL_TAX = "usf_tax"
COL_PROGRAMS = "usf_programs"
COL_META = "usf_meta"

# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
}

HTTP_TIMEOUT = 30.0


def _strip_html(html: str) -> str:
    if not html:
        return ""
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _hash(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()[:12]


# ═══════════════════════════════════════════════════════════════════════════
# 1. FINANCIAL NEWS
# ═══════════════════════════════════════════════════════════════════════════

# FRED (Federal Reserve Economic Data) — free JSON API
FRED_BASE = "https://api.stlouisfed.org/fred"
FRED_SERIES = {
    "UNRATE": "Unemployment Rate",
    "CPIAUCSL": "Consumer Price Index (CPI)",
    "FEDFUNDS": "Federal Funds Rate",
    "GDP": "Gross Domestic Product (GDP)",
    "DGS10": "10-Year Treasury Yield",
    "DGS2": "2-Year Treasury Yield",
    "MORTGAGE30US": "30-Year Mortgage Rate",
    "MORTGAGE15US": "15-Year Mortgage Rate",
    "HOUST": "Housing Starts",
    "PAYEMS": "Total Nonfarm Payrolls",
    "DEXCAUS": "USD/CAD Exchange Rate",
    "DCOILWTICO": "WTI Crude Oil Price",
}

# BLS (Bureau of Labor Statistics) — public JSON API
BLS_BASE = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
BLS_SERIES = {
    "LNS14000000": "Unemployment Rate",
    "CUUR0000SA0": "CPI All Urban Consumers",
    "CES0000000001": "Total Nonfarm Employment",
    "LAUCN040010000000003": "Local Area Unemployment",
}


@router.get("/news")
async def list_news(
    source: str = Query("fred", description="fred or bls"),
    limit: int = Query(50, ge=1, le=200),
    db=Depends(get_mongodb),
):
    """List scraped economic indicator data."""
    col = db[COL_NEWS]
    cursor = col.find({"source": source}).sort("scraped_at", -1).limit(limit)
    items = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        items.append(doc)
    return {"items": items}


@router.post("/news/scrape")
async def scrape_news(
    source: str = Query("fred", description="fred or bls"),
    db=Depends(get_mongodb),
):
    """Scrape financial news/indicators from selected source."""
    col = db[COL_NEWS]
    now = datetime.now(timezone.utc).isoformat()

    if source == "fred":
        items = await _scrape_fred(db)
    elif source == "bls":
        items = await _scrape_bls()
    else:
        raise HTTPException(400, "Invalid source. Use 'fred' or 'bls'.")

    saved = 0
    for item in items:
        item["source"] = source
        item["scraped_at"] = now
        # Upsert by series_id
        await col.update_one(
            {"series_id": item["series_id"], "source": source},
            {"$set": item},
            upsert=True,
        )
        saved += 1

    # Save scrape metadata
    await db[COL_META].update_one(
        {"key": f"news_scrape_{source}"},
        {"$set": {"last_scrape": now, "count": saved}},
        upsert=True,
    )

    return {"scraped": saved, "source": source}


async def _scrape_fred(db) -> list:
    """Fetch latest observations from FRED for key economic series."""
    # FRED requires an API key — use a demo key or user-provided
    settings_col = db["system_settings"]
    fred_key_doc = await settings_col.find_one({"key": "us_finance_fred_api_key"})
    # Default to FRED demo (limited but works for small usage)
    fred_key = (fred_key_doc or {}).get("value", "") or "DEMO_KEY"

    items = []
    async with httpx.AsyncClient(headers=HTTP_HEADERS, timeout=HTTP_TIMEOUT) as client:
        for series_id, label in FRED_SERIES.items():
            try:
                resp = await client.get(
                    f"{FRED_BASE}/series/observations",
                    params={
                        "series_id": series_id,
                        "api_key": fred_key,
                        "file_type": "json",
                        "sort_order": "desc",
                        "limit": 12,
                    },
                )
                if resp.status_code != 200:
                    logger.warning("FRED %s returned %s", series_id, resp.status_code)
                    continue
                data = resp.json()
                observations = data.get("observations", [])
                if not observations:
                    continue
                latest = observations[0]
                history = [
                    {"date": o["date"], "value": o["value"]}
                    for o in observations
                    if o["value"] != "."
                ]
                items.append({
                    "series_id": series_id,
                    "label": label,
                    "latest_value": latest.get("value", "N/A"),
                    "latest_date": latest.get("date", ""),
                    "history": history[:12],
                    "unit": _fred_unit(series_id),
                })
            except Exception as e:
                logger.error("FRED fetch %s error: %s", series_id, e)
    return items


def _fred_unit(series_id: str) -> str:
    pct = {"UNRATE", "FEDFUNDS", "DGS10", "DGS2", "MORTGAGE30US", "MORTGAGE15US"}
    if series_id in pct:
        return "%"
    if series_id == "DCOILWTICO":
        return "$/barrel"
    if series_id == "DEXCAUS":
        return "CAD/USD"
    if series_id in ("GDP",):
        return "Billions $"
    if series_id == "HOUST":
        return "Thousands"
    if series_id == "PAYEMS":
        return "Thousands"
    if series_id == "CPIAUCSL":
        return "Index"
    return ""


async def _scrape_bls() -> list:
    """Fetch latest data from BLS public API."""
    items = []
    year = datetime.now().year
    payload = {
        "seriesid": list(BLS_SERIES.keys()),
        "startyear": str(year - 1),
        "endyear": str(year),
    }
    try:
        async with httpx.AsyncClient(headers=HTTP_HEADERS, timeout=HTTP_TIMEOUT) as client:
            resp = await client.post(BLS_BASE, json=payload)
            if resp.status_code != 200:
                return items
            data = resp.json()
            for series in data.get("Results", {}).get("series", []):
                sid = series.get("seriesID", "")
                label = BLS_SERIES.get(sid, sid)
                obs = series.get("data", [])
                if not obs:
                    continue
                latest = obs[0]
                history = [
                    {"date": f"{o['year']}-{o['period'].replace('M', '')}", "value": o["value"]}
                    for o in obs[:12]
                ]
                items.append({
                    "series_id": sid,
                    "label": label,
                    "latest_value": latest.get("value", "N/A"),
                    "latest_date": f"{latest['year']}-{latest['period'].replace('M', '')}",
                    "history": history,
                    "unit": "%" if "Rate" in label else "",
                })
    except Exception as e:
        logger.error("BLS fetch error: %s", e)
    return items


@router.get("/news/scrape/status")
async def news_scrape_status(db=Depends(get_mongodb)):
    meta_fred = await db[COL_META].find_one({"key": "news_scrape_fred"})
    meta_bls = await db[COL_META].find_one({"key": "news_scrape_bls"})
    return {
        "fred": {"last_scrape": (meta_fred or {}).get("last_scrape"), "count": (meta_fred or {}).get("count", 0)},
        "bls": {"last_scrape": (meta_bls or {}).get("last_scrape"), "count": (meta_bls or {}).get("count", 0)},
    }


# ═══════════════════════════════════════════════════════════════════════════
# 2. REAL ESTATE — state-level indicators & trends
# ═══════════════════════════════════════════════════════════════════════════

REAL_ESTATE_FRED_SERIES = {
    "MSPUS": "Median Sales Price of Houses Sold (US)",
    "ASPUS": "Average Sales Price of Houses Sold (US)",
    "HOUST": "Housing Starts",
    "PERMIT": "Building Permits",
    "EXHOSLUSM495S": "Existing Home Sales",
    "RRVRUSQ156N": "Homeowner Vacancy Rate",
    "RRVRUSQ156N": "Rental Vacancy Rate",
    "CSUSHPINSA": "Case-Shiller US Home Price Index",
}


@router.get("/real-estate")
async def list_real_estate(
    limit: int = Query(50, ge=1, le=200),
    db=Depends(get_mongodb),
):
    col = db[COL_REAL_ESTATE]
    cursor = col.find().sort("scraped_at", -1).limit(limit)
    items = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        items.append(doc)
    return {"items": items}


@router.post("/real-estate/scrape")
async def scrape_real_estate(db=Depends(get_mongodb)):
    """Scrape real estate indicators from FRED."""
    settings_col = db["system_settings"]
    fred_key_doc = await settings_col.find_one({"key": "us_finance_fred_api_key"})
    fred_key = (fred_key_doc or {}).get("value", "") or "DEMO_KEY"

    col = db[COL_REAL_ESTATE]
    now = datetime.now(timezone.utc).isoformat()
    saved = 0

    async with httpx.AsyncClient(headers=HTTP_HEADERS, timeout=HTTP_TIMEOUT) as client:
        for series_id, label in REAL_ESTATE_FRED_SERIES.items():
            try:
                resp = await client.get(
                    f"{FRED_BASE}/series/observations",
                    params={
                        "series_id": series_id,
                        "api_key": fred_key,
                        "file_type": "json",
                        "sort_order": "desc",
                        "limit": 24,
                    },
                )
                if resp.status_code != 200:
                    continue
                data = resp.json()
                observations = data.get("observations", [])
                if not observations:
                    continue
                latest = observations[0]
                history = [
                    {"date": o["date"], "value": o["value"]}
                    for o in observations
                    if o["value"] != "."
                ]
                item = {
                    "series_id": series_id,
                    "label": label,
                    "latest_value": latest.get("value", "N/A"),
                    "latest_date": latest.get("date", ""),
                    "history": history[:24],
                    "scraped_at": now,
                }
                await col.update_one(
                    {"series_id": series_id},
                    {"$set": item},
                    upsert=True,
                )
                saved += 1
            except Exception as e:
                logger.error("RE FRED %s error: %s", series_id, e)

    await db[COL_META].update_one(
        {"key": "real_estate_scrape"},
        {"$set": {"last_scrape": now, "count": saved}},
        upsert=True,
    )
    return {"scraped": saved}


# ═══════════════════════════════════════════════════════════════════════════
# 3. PROPERTY VALUATION — LLM-powered neighborhood analysis
# ═══════════════════════════════════════════════════════════════════════════

class ValuationRequest(BaseModel):
    address: str
    bedrooms: int = 3
    bathrooms: int = 2
    floors: int = 1
    year_built: int = 2000
    lot_size_sqft: int = 5000
    condition: str = "good"  # "poor", "good", "excellent"
    notes: str = ""


@router.get("/valuations")
async def list_valuations(
    address: str = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db=Depends(get_mongodb),
):
    col = db[COL_VALUATIONS]
    query = {}
    if address:
        query["address"] = {"$regex": address, "$options": "i"}
    cursor = col.find(query).sort("created_at", -1).limit(limit)
    items = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        items.append(doc)
    return {"items": items}


@router.post("/valuations")
async def create_valuation(
    body: ValuationRequest,
    db=Depends(get_mongodb),
):
    """Create a property valuation request — uses LLM for analysis."""
    col = db[COL_VALUATIONS]
    now = datetime.now(timezone.utc).isoformat()

    # First try to fetch neighborhood data from web
    neighborhood_data = await _fetch_neighborhood_data(body.address)

    doc = {
        "address": body.address,
        "bedrooms": body.bedrooms,
        "bathrooms": body.bathrooms,
        "floors": body.floors,
        "year_built": body.year_built,
        "lot_size_sqft": body.lot_size_sqft,
        "condition": body.condition,
        "notes": body.notes,
        "neighborhood_data": neighborhood_data,
        "analysis": None,  # Will be filled by LLM call from frontend
        "estimated_value": None,
        "created_at": now,
        "status": "pending",
    }
    result = await col.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return doc


@router.patch("/valuations/{valuation_id}")
async def update_valuation(
    valuation_id: str,
    body: dict = Body(...),
    db=Depends(get_mongodb),
):
    """Update valuation with analysis results from LLM."""
    from bson import ObjectId
    col = db[COL_VALUATIONS]
    update = {}
    for field in ("analysis", "estimated_value", "status", "comparable_sales"):
        if field in body:
            update[field] = body[field]
    if update:
        update["updated_at"] = datetime.now(timezone.utc).isoformat()
        await col.update_one({"_id": ObjectId(valuation_id)}, {"$set": update})
    # Return updated doc
    doc = await col.find_one({"_id": ObjectId(valuation_id)})
    if doc:
        doc["_id"] = str(doc["_id"])
    return doc or {}


@router.delete("/valuations/{valuation_id}")
async def delete_valuation(valuation_id: str, db=Depends(get_mongodb)):
    from bson import ObjectId
    await db[COL_VALUATIONS].delete_one({"_id": ObjectId(valuation_id)})
    return {"detail": "Deleted"}


async def _fetch_neighborhood_data(address: str) -> dict:
    """Try to get neighborhood/comparable data from public sources."""
    data = {"address": address, "sources": []}
    try:
        async with httpx.AsyncClient(headers=HTTP_HEADERS, timeout=15.0) as client:
            # Use Nominatim for geocoding (free, no API key)
            geo_resp = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": address, "format": "json", "limit": 1},
                headers={**HTTP_HEADERS, "User-Agent": "BabberFinance/1.0"},
            )
            if geo_resp.status_code == 200:
                geo = geo_resp.json()
                if geo:
                    data["lat"] = geo[0].get("lat")
                    data["lon"] = geo[0].get("lon")
                    data["display_name"] = geo[0].get("display_name", "")
                    data["sources"].append("nominatim")
    except Exception as e:
        logger.warning("Geocoding failed for %s: %s", address, e)
    return data


# ═══════════════════════════════════════════════════════════════════════════
# 4. PROPERTY SEARCH — auction monitoring
# ═══════════════════════════════════════════════════════════════════════════

class PropertySearchParams(BaseModel):
    min_price: Optional[int] = None
    max_price: Optional[int] = None
    min_bedrooms: Optional[int] = None
    state: Optional[str] = None
    property_type: Optional[str] = None  # "house", "condo", "land"
    keywords: Optional[str] = None


@router.get("/property-search/criteria")
async def get_search_criteria(db=Depends(get_mongodb)):
    """Get saved search criteria."""
    doc = await db[COL_META].find_one({"key": "property_search_criteria"})
    if doc:
        doc.pop("_id", None)
    return doc or {"key": "property_search_criteria", "criteria": {}}


@router.post("/property-search/criteria")
async def save_search_criteria(
    body: PropertySearchParams,
    db=Depends(get_mongodb),
):
    """Save property search filter criteria."""
    await db[COL_META].update_one(
        {"key": "property_search_criteria"},
        {"$set": {"criteria": body.dict(), "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    return {"detail": "Criteria saved"}


@router.get("/property-search/items")
async def list_auction_items(
    limit: int = Query(100, ge=1, le=500),
    matched_only: bool = Query(False),
    db=Depends(get_mongodb),
):
    """List scraped auction items."""
    col = db[COL_AUCTION_ITEMS]
    query = {}
    if matched_only:
        query["matched"] = True
    cursor = col.find(query).sort("scraped_at", -1).limit(limit)
    items = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        items.append(doc)
    return {"items": items, "total": await col.count_documents(query)}


@router.post("/property-search/scrape")
async def scrape_auctions(db=Depends(get_mongodb)):
    """Scrape auction URLs from settings."""
    settings_col = db["system_settings"]
    urls_doc = await settings_col.find_one({"key": "us_finance_auction_urls"})
    raw_urls = (urls_doc or {}).get("value", "")
    if not raw_urls:
        return {"scraped": 0, "message": "No auction URLs configured in settings"}

    urls = [u.strip() for u in raw_urls.split("\n") if u.strip()]
    col = db[COL_AUCTION_ITEMS]
    now = datetime.now(timezone.utc).isoformat()
    saved = 0

    # Load search criteria for matching
    criteria_doc = await db[COL_META].find_one({"key": "property_search_criteria"})
    criteria = (criteria_doc or {}).get("criteria", {})

    async with httpx.AsyncClient(headers=HTTP_HEADERS, timeout=HTTP_TIMEOUT, follow_redirects=True) as client:
        for url in urls:
            try:
                resp = await client.get(url)
                if resp.status_code != 200:
                    logger.warning("Auction URL %s returned %s", url, resp.status_code)
                    continue
                # Parse HTML for property listings
                listings = _parse_auction_page(resp.text, url)
                for listing in listings:
                    listing["source_url"] = url
                    listing["scraped_at"] = now
                    listing["matched"] = _matches_criteria(listing, criteria)
                    await col.update_one(
                        {"uid": listing["uid"]},
                        {"$set": listing},
                        upsert=True,
                    )
                    saved += 1
            except Exception as e:
                logger.error("Auction scrape %s error: %s", url, e)

    await db[COL_META].update_one(
        {"key": "auction_scrape"},
        {"$set": {"last_scrape": now, "count": saved}},
        upsert=True,
    )
    return {"scraped": saved}


def _parse_auction_page(html: str, url: str) -> list:
    """Basic HTML parser for auction listings. Returns structured items."""
    listings = []
    # Generic extraction — look for common property listing patterns
    # This is a best-effort parser; real auction sites vary widely
    blocks = re.findall(
        r'<(?:div|article|li)[^>]*class="[^"]*(?:listing|property|item|result)[^"]*"[^>]*>(.*?)</(?:div|article|li)>',
        html, re.DOTALL | re.IGNORECASE
    )
    for i, block in enumerate(blocks[:100]):
        title = ""
        price = ""
        address = ""

        title_match = re.search(r'<(?:h[2-4]|a)[^>]*>([^<]+)</(?:h[2-4]|a)>', block)
        if title_match:
            title = _strip_html(title_match.group(1)).strip()

        price_match = re.search(r'\$[\d,]+(?:\.\d{2})?', block)
        if price_match:
            price = price_match.group(0)

        addr_match = re.search(r'(?:address|location)[^>]*>([^<]+)<', block, re.IGNORECASE)
        if addr_match:
            address = _strip_html(addr_match.group(1)).strip()

        if title or price:
            uid = _hash(f"{url}:{title}:{price}:{i}")
            listings.append({
                "uid": uid,
                "title": title,
                "price_raw": price,
                "price_num": _parse_price(price),
                "address": address,
                "body_snippet": _strip_html(block)[:500],
            })
    return listings


def _parse_price(raw: str) -> Optional[int]:
    if not raw:
        return None
    nums = re.sub(r'[^\d]', '', raw)
    return int(nums) if nums else None


def _matches_criteria(listing: dict, criteria: dict) -> bool:
    """Check if a listing matches saved search criteria."""
    if not criteria:
        return False
    price = listing.get("price_num")
    if price:
        if criteria.get("min_price") and price < criteria["min_price"]:
            return False
        if criteria.get("max_price") and price > criteria["max_price"]:
            return False
    if criteria.get("keywords"):
        text = f"{listing.get('title', '')} {listing.get('address', '')} {listing.get('body_snippet', '')}".lower()
        keywords = criteria["keywords"].lower().split()
        if not any(kw in text for kw in keywords):
            return False
    if criteria.get("state"):
        addr = (listing.get("address") or "").upper()
        if criteria["state"].upper() not in addr:
            return False
    return True


# ═══════════════════════════════════════════════════════════════════════════
# 5. OIL — crude oil & energy prices
# ═══════════════════════════════════════════════════════════════════════════

OIL_FRED_SERIES = {
    "DCOILWTICO": "WTI Crude Oil",
    "DCOILBRENTEU": "Brent Crude Oil",
    "DHHNGSP": "Henry Hub Natural Gas",
    "GASREGW": "US Regular Gasoline Price",
}


@router.get("/oil")
async def list_oil(db=Depends(get_mongodb)):
    col = db[COL_OIL]
    cursor = col.find().sort("scraped_at", -1)
    items = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        items.append(doc)
    return {"items": items}


@router.post("/oil/scrape")
async def scrape_oil(db=Depends(get_mongodb)):
    """Scrape oil/energy prices from FRED."""
    settings_col = db["system_settings"]
    fred_key_doc = await settings_col.find_one({"key": "us_finance_fred_api_key"})
    fred_key = (fred_key_doc or {}).get("value", "") or "DEMO_KEY"

    col = db[COL_OIL]
    now = datetime.now(timezone.utc).isoformat()
    saved = 0

    async with httpx.AsyncClient(headers=HTTP_HEADERS, timeout=HTTP_TIMEOUT) as client:
        for series_id, label in OIL_FRED_SERIES.items():
            try:
                resp = await client.get(
                    f"{FRED_BASE}/series/observations",
                    params={
                        "series_id": series_id,
                        "api_key": fred_key,
                        "file_type": "json",
                        "sort_order": "desc",
                        "limit": 60,
                    },
                )
                if resp.status_code != 200:
                    continue
                data = resp.json()
                observations = data.get("observations", [])
                if not observations:
                    continue
                latest = observations[0]
                history = [
                    {"date": o["date"], "value": o["value"]}
                    for o in observations
                    if o["value"] != "."
                ]
                item = {
                    "series_id": series_id,
                    "label": label,
                    "latest_value": latest.get("value", "N/A"),
                    "latest_date": latest.get("date", ""),
                    "history": history[:60],
                    "unit": "$/barrel" if "Crude" in label else ("$/MMBtu" if "Gas" in label and "Natural" in label else "$/gallon"),
                    "scraped_at": now,
                }
                await col.update_one(
                    {"series_id": series_id},
                    {"$set": item},
                    upsert=True,
                )
                saved += 1
            except Exception as e:
                logger.error("Oil FRED %s error: %s", series_id, e)

    await db[COL_META].update_one(
        {"key": "oil_scrape"},
        {"$set": {"last_scrape": now, "count": saved}},
        upsert=True,
    )
    return {"scraped": saved}


# ═══════════════════════════════════════════════════════════════════════════
# 6. TAXATION — US state tax data
# ═══════════════════════════════════════════════════════════════════════════

# Pre-seeded US state tax data (sourced from Tax Foundation / public data)
US_STATES_TAX = [
    {"state": "Alabama", "abbr": "AL", "income_tax": "2% - 5%", "sales_tax": "4%", "property_tax": "0.40%", "no_income_tax": False, "notes": "Deductible federal income tax"},
    {"state": "Alaska", "abbr": "AK", "income_tax": "None", "sales_tax": "None", "property_tax": "1.07%", "no_income_tax": True, "notes": "No state income or sales tax; PFD dividend"},
    {"state": "Arizona", "abbr": "AZ", "income_tax": "2.5% flat", "sales_tax": "5.6%", "property_tax": "0.62%", "no_income_tax": False, "notes": "Flat tax since 2023"},
    {"state": "Arkansas", "abbr": "AR", "income_tax": "2% - 4.4%", "sales_tax": "6.5%", "property_tax": "0.63%", "no_income_tax": False, "notes": ""},
    {"state": "California", "abbr": "CA", "income_tax": "1% - 13.3%", "sales_tax": "7.25%", "property_tax": "0.71%", "no_income_tax": False, "notes": "Highest top marginal rate in US"},
    {"state": "Colorado", "abbr": "CO", "income_tax": "4.4% flat", "sales_tax": "2.9%", "property_tax": "0.49%", "no_income_tax": False, "notes": "TABOR limits"},
    {"state": "Connecticut", "abbr": "CT", "income_tax": "3% - 6.99%", "sales_tax": "6.35%", "property_tax": "2.15%", "no_income_tax": False, "notes": ""},
    {"state": "Delaware", "abbr": "DE", "income_tax": "2.2% - 6.6%", "sales_tax": "None", "property_tax": "0.57%", "no_income_tax": False, "notes": "No sales tax; corporate-friendly laws"},
    {"state": "Florida", "abbr": "FL", "income_tax": "None", "sales_tax": "6%", "property_tax": "0.86%", "no_income_tax": True, "notes": "No state income tax"},
    {"state": "Georgia", "abbr": "GA", "income_tax": "5.49% flat", "sales_tax": "4%", "property_tax": "0.91%", "no_income_tax": False, "notes": "Moving to flat tax"},
    {"state": "Hawaii", "abbr": "HI", "income_tax": "1.4% - 11%", "sales_tax": "4%", "property_tax": "0.28%", "no_income_tax": False, "notes": "Lowest property tax rate"},
    {"state": "Idaho", "abbr": "ID", "income_tax": "5.695% flat", "sales_tax": "6%", "property_tax": "0.63%", "no_income_tax": False, "notes": ""},
    {"state": "Illinois", "abbr": "IL", "income_tax": "4.95% flat", "sales_tax": "6.25%", "property_tax": "2.07%", "no_income_tax": False, "notes": "High property taxes"},
    {"state": "Indiana", "abbr": "IN", "income_tax": "3.05% flat", "sales_tax": "7%", "property_tax": "0.83%", "no_income_tax": False, "notes": ""},
    {"state": "Iowa", "abbr": "IA", "income_tax": "4.4% - 5.7%", "sales_tax": "6%", "property_tax": "1.52%", "no_income_tax": False, "notes": "Reducing rates through 2026"},
    {"state": "Kansas", "abbr": "KS", "income_tax": "3.1% - 5.7%", "sales_tax": "6.5%", "property_tax": "1.41%", "no_income_tax": False, "notes": ""},
    {"state": "Kentucky", "abbr": "KY", "income_tax": "4% flat", "sales_tax": "6%", "property_tax": "0.86%", "no_income_tax": False, "notes": ""},
    {"state": "Louisiana", "abbr": "LA", "income_tax": "1.85% - 4.25%", "sales_tax": "4.45%", "property_tax": "0.56%", "no_income_tax": False, "notes": ""},
    {"state": "Maine", "abbr": "ME", "income_tax": "5.8% - 7.15%", "sales_tax": "5.5%", "property_tax": "1.30%", "no_income_tax": False, "notes": ""},
    {"state": "Maryland", "abbr": "MD", "income_tax": "2% - 5.75%", "sales_tax": "6%", "property_tax": "1.07%", "no_income_tax": False, "notes": "Local income tax also applies"},
    {"state": "Massachusetts", "abbr": "MA", "income_tax": "5% / 9% (>$1M)", "sales_tax": "6.25%", "property_tax": "1.17%", "no_income_tax": False, "notes": "Millionaire surtax 4%"},
    {"state": "Michigan", "abbr": "MI", "income_tax": "4.25% flat", "sales_tax": "6%", "property_tax": "1.38%", "no_income_tax": False, "notes": ""},
    {"state": "Minnesota", "abbr": "MN", "income_tax": "5.35% - 9.85%", "sales_tax": "6.875%", "property_tax": "1.08%", "no_income_tax": False, "notes": ""},
    {"state": "Mississippi", "abbr": "MS", "income_tax": "4.7% flat", "sales_tax": "7%", "property_tax": "0.67%", "no_income_tax": False, "notes": "Moving toward no income tax"},
    {"state": "Missouri", "abbr": "MO", "income_tax": "2% - 4.8%", "sales_tax": "4.225%", "property_tax": "0.97%", "no_income_tax": False, "notes": ""},
    {"state": "Montana", "abbr": "MT", "income_tax": "4.7% flat", "sales_tax": "None", "property_tax": "0.74%", "no_income_tax": False, "notes": "No sales tax"},
    {"state": "Nebraska", "abbr": "NE", "income_tax": "2.46% - 5.84%", "sales_tax": "5.5%", "property_tax": "1.61%", "no_income_tax": False, "notes": ""},
    {"state": "Nevada", "abbr": "NV", "income_tax": "None", "sales_tax": "6.85%", "property_tax": "0.53%", "no_income_tax": True, "notes": "No state income tax"},
    {"state": "New Hampshire", "abbr": "NH", "income_tax": "None (interest only)", "sales_tax": "None", "property_tax": "1.93%", "no_income_tax": True, "notes": "No income or sales tax; high property tax"},
    {"state": "New Jersey", "abbr": "NJ", "income_tax": "1.4% - 10.75%", "sales_tax": "6.625%", "property_tax": "2.47%", "no_income_tax": False, "notes": "Highest property tax rate in US"},
    {"state": "New Mexico", "abbr": "NM", "income_tax": "1.7% - 5.9%", "sales_tax": "5.125%", "property_tax": "0.67%", "no_income_tax": False, "notes": ""},
    {"state": "New York", "abbr": "NY", "income_tax": "4% - 10.9%", "sales_tax": "4%", "property_tax": "1.72%", "no_income_tax": False, "notes": "NYC additional income tax up to 3.876%"},
    {"state": "North Carolina", "abbr": "NC", "income_tax": "4.5% flat", "sales_tax": "4.75%", "property_tax": "0.80%", "no_income_tax": False, "notes": "Reducing toward 0% by 2030"},
    {"state": "North Dakota", "abbr": "ND", "income_tax": "0% - 2.5%", "sales_tax": "5%", "property_tax": "0.98%", "no_income_tax": False, "notes": "Near-zero for most residents"},
    {"state": "Ohio", "abbr": "OH", "income_tax": "0% - 3.5%", "sales_tax": "5.75%", "property_tax": "1.53%", "no_income_tax": False, "notes": "No tax on first $26,050"},
    {"state": "Oklahoma", "abbr": "OK", "income_tax": "0.25% - 4.75%", "sales_tax": "4.5%", "property_tax": "0.88%", "no_income_tax": False, "notes": ""},
    {"state": "Oregon", "abbr": "OR", "income_tax": "4.75% - 9.9%", "sales_tax": "None", "property_tax": "0.93%", "no_income_tax": False, "notes": "No sales tax"},
    {"state": "Pennsylvania", "abbr": "PA", "income_tax": "3.07% flat", "sales_tax": "6%", "property_tax": "1.53%", "no_income_tax": False, "notes": "Low flat rate"},
    {"state": "Rhode Island", "abbr": "RI", "income_tax": "3.75% - 5.99%", "sales_tax": "7%", "property_tax": "1.53%", "no_income_tax": False, "notes": ""},
    {"state": "South Carolina", "abbr": "SC", "income_tax": "0% - 6.4%", "sales_tax": "6%", "property_tax": "0.57%", "no_income_tax": False, "notes": ""},
    {"state": "South Dakota", "abbr": "SD", "income_tax": "None", "sales_tax": "4.5%", "property_tax": "1.22%", "no_income_tax": True, "notes": "No state income tax; trust-friendly"},
    {"state": "Tennessee", "abbr": "TN", "income_tax": "None", "sales_tax": "7%", "property_tax": "0.64%", "no_income_tax": True, "notes": "No state income tax; high sales tax"},
    {"state": "Texas", "abbr": "TX", "income_tax": "None", "sales_tax": "6.25%", "property_tax": "1.68%", "no_income_tax": True, "notes": "No income tax; high property tax"},
    {"state": "Utah", "abbr": "UT", "income_tax": "4.65% flat", "sales_tax": "6.1%", "property_tax": "0.58%", "no_income_tax": False, "notes": ""},
    {"state": "Vermont", "abbr": "VT", "income_tax": "3.35% - 8.75%", "sales_tax": "6%", "property_tax": "1.90%", "no_income_tax": False, "notes": ""},
    {"state": "Virginia", "abbr": "VA", "income_tax": "2% - 5.75%", "sales_tax": "5.3%", "property_tax": "0.82%", "no_income_tax": False, "notes": ""},
    {"state": "Washington", "abbr": "WA", "income_tax": "None (7% cap gains)", "sales_tax": "6.5%", "property_tax": "0.98%", "no_income_tax": True, "notes": "No income tax; 7% on cap gains >$270k"},
    {"state": "West Virginia", "abbr": "WV", "income_tax": "2.36% - 5.12%", "sales_tax": "6%", "property_tax": "0.57%", "no_income_tax": False, "notes": "Reducing rates"},
    {"state": "Wisconsin", "abbr": "WI", "income_tax": "3.5% - 7.65%", "sales_tax": "5%", "property_tax": "1.73%", "no_income_tax": False, "notes": ""},
    {"state": "Wyoming", "abbr": "WY", "income_tax": "None", "sales_tax": "4%", "property_tax": "0.56%", "no_income_tax": True, "notes": "No state income tax"},
]

# Corporate/LLC tax by state (simplified)
US_STATES_CORP_TAX = [
    {"state": "Alabama", "abbr": "AL", "corp_tax": "6.5%", "franchise_tax": "Yes", "llc_fee": "$100/yr", "notes": ""},
    {"state": "Alaska", "abbr": "AK", "corp_tax": "0% - 9.4%", "franchise_tax": "No", "llc_fee": "$100 biennial", "notes": "Graduated corporate tax"},
    {"state": "California", "abbr": "CA", "corp_tax": "8.84%", "franchise_tax": "$800 min", "llc_fee": "$800 min + gross receipts fee", "notes": "High minimum franchise tax"},
    {"state": "Delaware", "abbr": "DE", "corp_tax": "8.7%", "franchise_tax": "$175-$200k+", "llc_fee": "$300/yr", "notes": "Most popular for incorporation"},
    {"state": "Florida", "abbr": "FL", "corp_tax": "5.5%", "franchise_tax": "No", "llc_fee": "$138.75/yr", "notes": "No personal income tax"},
    {"state": "Nevada", "abbr": "NV", "corp_tax": "None", "franchise_tax": "No", "llc_fee": "$350/yr", "notes": "No corporate income tax"},
    {"state": "New York", "abbr": "NY", "corp_tax": "6.5% - 7.25%", "franchise_tax": "Yes", "llc_fee": "$25 filing", "notes": "Additional MTA surcharge in NYC area"},
    {"state": "Texas", "abbr": "TX", "corp_tax": "Margin tax 0.375%-0.75%", "franchise_tax": "Yes", "llc_fee": "$300", "notes": "Franchise/margin tax instead of income tax"},
    {"state": "Washington", "abbr": "WA", "corp_tax": "None (B&O tax)", "franchise_tax": "No", "llc_fee": "$60/yr", "notes": "Business & Occupation tax instead"},
    {"state": "Wyoming", "abbr": "WY", "corp_tax": "None", "franchise_tax": "No", "llc_fee": "$60/yr", "notes": "Very business-friendly; no income/franchise tax"},
]


@router.get("/taxation/individual")
async def get_individual_tax():
    """Return individual tax data for all US states."""
    return {"items": US_STATES_TAX}


@router.get("/taxation/corporate")
async def get_corporate_tax():
    """Return corporate/LLC tax data for US states."""
    return {"items": US_STATES_CORP_TAX}


# ═══════════════════════════════════════════════════════════════════════════
# 7. PROGRAMS — government financing programs by state
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/programs")
async def list_programs(
    state: str = Query(None),
    program_type: str = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db=Depends(get_mongodb),
):
    col = db[COL_PROGRAMS]
    query = {}
    if state:
        query["state"] = {"$regex": state, "$options": "i"}
    if program_type:
        query["program_type"] = program_type
    cursor = col.find(query).sort("state", 1).limit(limit)
    items = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        items.append(doc)
    return {"items": items, "total": await col.count_documents(query)}


@router.post("/programs/scrape")
async def scrape_programs(db=Depends(get_mongodb)):
    """Scrape government financing programs from public sources."""
    col = db[COL_PROGRAMS]
    now = datetime.now(timezone.utc).isoformat()

    # Scrape from grants.gov and SBA
    programs = []
    programs.extend(await _scrape_sba_programs())
    programs.extend(await _scrape_grants_gov())

    saved = 0
    for prog in programs:
        prog["scraped_at"] = now
        await col.update_one(
            {"uid": prog["uid"]},
            {"$set": prog},
            upsert=True,
        )
        saved += 1

    await db[COL_META].update_one(
        {"key": "programs_scrape"},
        {"$set": {"last_scrape": now, "count": saved}},
        upsert=True,
    )
    return {"scraped": saved}


async def _scrape_sba_programs() -> list:
    """Scrape SBA (Small Business Administration) resources."""
    programs = []
    try:
        async with httpx.AsyncClient(headers=HTTP_HEADERS, timeout=HTTP_TIMEOUT) as client:
            # SBA resource partners directory
            resp = await client.get("https://www.sba.gov/api/content/search/directory.json?moab=localassistance&pageNumber=1&pageSize=50")
            if resp.status_code == 200:
                data = resp.json()
                for item in (data.get("items") or data if isinstance(data, list) else []):
                    if isinstance(item, dict):
                        programs.append({
                            "uid": _hash(f"sba:{item.get('title', '')}"),
                            "title": item.get("title", "SBA Program"),
                            "description": _strip_html(item.get("body", "") or item.get("description", "")),
                            "state": item.get("state", "National"),
                            "program_type": "sba",
                            "url": item.get("url") or f"https://www.sba.gov",
                            "source": "sba.gov",
                        })
    except Exception as e:
        logger.warning("SBA scrape error: %s", e)

    # Fallback: return well-known SBA programs
    if not programs:
        known_programs = [
            {"title": "SBA 7(a) Loan Program", "description": "Most common SBA loan — up to $5M for working capital, equipment, real estate", "url": "https://www.sba.gov/funding-programs/loans/7a-loans", "state": "National"},
            {"title": "SBA 504 Loan Program", "description": "Long-term, fixed-rate financing for major assets like real estate and equipment", "url": "https://www.sba.gov/funding-programs/loans/504-loans", "state": "National"},
            {"title": "SBA Microloan Program", "description": "Small loans up to $50,000 for startups and small businesses", "url": "https://www.sba.gov/funding-programs/loans/microloans", "state": "National"},
            {"title": "SBIR / STTR Grants", "description": "Federal research grants for small businesses — up to $2M", "url": "https://www.sbir.gov", "state": "National"},
            {"title": "SBA Disaster Loans", "description": "Low-interest loans for businesses and homeowners affected by disasters", "url": "https://www.sba.gov/funding-programs/disaster-assistance", "state": "National"},
        ]
        for p in known_programs:
            p["uid"] = _hash(f"sba:{p['title']}")
            p["program_type"] = "sba"
            p["source"] = "sba.gov"
            programs.append(p)

    return programs


async def _scrape_grants_gov() -> list:
    """Scrape grants.gov for relevant financing opportunities."""
    programs = []
    try:
        async with httpx.AsyncClient(headers=HTTP_HEADERS, timeout=HTTP_TIMEOUT) as client:
            # Grants.gov public search API
            resp = await client.post(
                "https://www.grants.gov/grantsws/rest/opportunities/search",
                json={
                    "keyword": "small business financing",
                    "rows": 25,
                    "sortBy": "openDate|desc",
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                for opp in (data.get("oppHits") or []):
                    programs.append({
                        "uid": _hash(f"grants:{opp.get('id', '')}"),
                        "title": opp.get("title", ""),
                        "description": opp.get("synopsis", "") or opp.get("description", ""),
                        "state": "National",
                        "program_type": "grant",
                        "url": f"https://www.grants.gov/search-results-detail/{opp.get('id', '')}",
                        "source": "grants.gov",
                        "close_date": opp.get("closeDate"),
                        "agency": opp.get("agency", ""),
                        "award_ceiling": opp.get("awardCeiling"),
                    })
    except Exception as e:
        logger.warning("Grants.gov scrape error: %s", e)
    return programs


# ═══════════════════════════════════════════════════════════════════════════
# General endpoints
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/stats")
async def get_stats(db=Depends(get_mongodb)):
    """Counts per section."""
    return {
        "news": await db[COL_NEWS].count_documents({}),
        "real_estate": await db[COL_REAL_ESTATE].count_documents({}),
        "valuations": await db[COL_VALUATIONS].count_documents({}),
        "auction_items": await db[COL_AUCTION_ITEMS].count_documents({}),
        "matched_auctions": await db[COL_AUCTION_ITEMS].count_documents({"matched": True}),
        "oil": await db[COL_OIL].count_documents({}),
        "programs": await db[COL_PROGRAMS].count_documents({}),
    }


@router.get("/scrape/status")
async def scrape_status(db=Depends(get_mongodb)):
    """All scrape metadata."""
    keys = ["news_scrape_fred", "news_scrape_bls", "real_estate_scrape", "auction_scrape", "oil_scrape", "programs_scrape"]
    result = {}
    for key in keys:
        doc = await db[COL_META].find_one({"key": key})
        result[key] = {"last_scrape": (doc or {}).get("last_scrape"), "count": (doc or {}).get("count", 0)}
    return result


@router.post("/scrape-all")
async def scrape_all(db=Depends(get_mongodb)):
    """Run all scrapers."""
    results = {}
    try:
        r = await scrape_news(source="fred", db=db)
        results["fred"] = r
    except Exception as e:
        results["fred"] = {"error": str(e)}
    try:
        r = await scrape_news(source="bls", db=db)
        results["bls"] = r
    except Exception as e:
        results["bls"] = {"error": str(e)}
    try:
        r = await scrape_real_estate(db=db)
        results["real_estate"] = r
    except Exception as e:
        results["real_estate"] = {"error": str(e)}
    try:
        r = await scrape_oil(db=db)
        results["oil"] = r
    except Exception as e:
        results["oil"] = {"error": str(e)}
    try:
        r = await scrape_programs(db=db)
        results["programs"] = r
    except Exception as e:
        results["programs"] = {"error": str(e)}
    try:
        r = await scrape_auctions(db=db)
        results["auctions"] = r
    except Exception as e:
        results["auctions"] = {"error": str(e)}
    return results


@router.delete("/clear")
async def clear_all_data(db=Depends(get_mongodb)):
    """Delete all addon data."""
    for col_name in [COL_NEWS, COL_REAL_ESTATE, COL_VALUATIONS, COL_PROPERTY_SEARCH,
                     COL_AUCTION_ITEMS, COL_OIL, COL_TAX, COL_PROGRAMS, COL_META]:
        await db[col_name].drop()
    return {"detail": "All data cleared"}
