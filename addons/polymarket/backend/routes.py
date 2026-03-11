"""
Polymarket Addon — Backend routes.

Proxies calls to Polymarket CLOB API (https://clob.polymarket.com)
and Gamma API (https://gamma-api.polymarket.com) for event data.

All endpoints require authentication and polymarket_api_key setting.
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, List

import httpx
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_mongodb
from app.core.dependencies import get_current_user
from app.api.settings import get_setting_value

logger = logging.getLogger("addon.polymarket")

router = APIRouter(
    prefix="/api/addons/polymarket",
    tags=["addon-polymarket"],
    dependencies=[Depends(get_current_user)],
)

GAMMA_API = "https://gamma-api.polymarket.com"
CLOB_API = "https://clob.polymarket.com"


async def _get_polymarket_creds(db) -> dict:
    """Get Polymarket API credentials from system settings."""
    api_key = await get_setting_value(db, "polymarket_api_key")
    api_secret = await get_setting_value(db, "polymarket_api_secret")
    passphrase = await get_setting_value(db, "polymarket_passphrase")
    return {
        "api_key": api_key or "",
        "api_secret": api_secret or "",
        "passphrase": passphrase or "",
    }


def _clob_headers(creds: dict) -> dict:
    """Build headers for CLOB API calls."""
    headers = {"Content-Type": "application/json"}
    if creds["api_key"]:
        headers["POLY_API_KEY"] = creds["api_key"]
        headers["POLY_API_SECRET"] = creds["api_secret"]
        headers["POLY_PASSPHRASE"] = creds["passphrase"]
    return headers


def _parse_outcome_prices(raw) -> dict:
    """Parse outcomePrices from Gamma API — can be a JSON string or list."""
    if not raw:
        return {"outcome_yes": None, "outcome_no": None}
    try:
        prices = json.loads(raw) if isinstance(raw, str) else raw
        yes = float(prices[0]) if len(prices) > 0 and prices[0] is not None else None
        no = float(prices[1]) if len(prices) > 1 and prices[1] is not None else None
        return {"outcome_yes": yes, "outcome_no": no}
    except (json.JSONDecodeError, TypeError, ValueError, IndexError):
        return {"outcome_yes": None, "outcome_no": None}


def _parse_token_ids(raw) -> dict:
    """Parse clobTokenIds — may be JSON string or list."""
    if not raw:
        return {"token_id_yes": None, "token_id_no": None}
    try:
        ids = json.loads(raw) if isinstance(raw, str) else raw
        return {
            "token_id_yes": ids[0] if len(ids) > 0 else None,
            "token_id_no": ids[1] if len(ids) > 1 else None,
        }
    except (json.JSONDecodeError, TypeError, ValueError, IndexError):
        return {"token_id_yes": None, "token_id_no": None}


# ─── Events (public, no auth needed) ───

@router.get("/events")
async def list_events(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    active: bool = Query(True),
    closed: bool = Query(False),
    search: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """List prediction market events from Gamma API."""
    params = {"limit": limit, "offset": offset, "active": str(active).lower(), "closed": str(closed).lower()}
    if search:
        params["tag"] = search
    try:
        async with httpx.AsyncClient(timeout=15, verify=False) as client:
            r = await client.get(f"{GAMMA_API}/events", params=params)
            if r.status_code != 200:
                raise HTTPException(status_code=r.status_code, detail=f"Gamma API error: {r.text[:500]}")
            events = r.json()
            # Enrich with market data
            result = []
            for ev in events:
                markets = ev.get("markets", [])
                result.append({
                    "id": ev.get("id"),
                    "slug": ev.get("slug"),
                    "title": ev.get("title"),
                    "description": ev.get("description", "")[:300],
                    "start_date": ev.get("startDate"),
                    "end_date": ev.get("endDate"),
                    "active": ev.get("active"),
                    "closed": ev.get("closed"),
                    "liquidity": ev.get("liquidity"),
                    "volume": ev.get("volume"),
                    "markets_count": len(markets),
                    "markets": [
                        {
                            "id": m.get("id"),
                            "question": m.get("question"),
                            **_parse_outcome_prices(m.get("outcomePrices")),
                            "volume": m.get("volume"),
                            "liquidity": m.get("liquidity"),
                            "active": m.get("active"),
                        }
                        for m in markets[:10]
                    ],
                })
            return {"items": result, "total": len(result), "offset": offset, "limit": limit}
    except httpx.HTTPError as e:
        logger.error("Polymarket events fetch error: %s", e)
        raise HTTPException(status_code=502, detail=f"Error connecting to Polymarket: {e}")


@router.get("/events/{event_id}")
async def get_event(event_id: str, db: AsyncIOMotorDatabase = Depends(get_mongodb)):
    """Get detailed event info with all markets."""
    try:
        async with httpx.AsyncClient(timeout=15, verify=False) as client:
            r = await client.get(f"{GAMMA_API}/events/{event_id}")
            if r.status_code == 404:
                raise HTTPException(status_code=404, detail="Event not found")
            if r.status_code != 200:
                raise HTTPException(status_code=r.status_code, detail=f"Gamma API error: {r.text[:500]}")
            return r.json()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/markets/{token_id}/orderbook")
async def get_orderbook(token_id: str, db: AsyncIOMotorDatabase = Depends(get_mongodb)):
    """Get orderbook for a specific market outcome token."""
    try:
        async with httpx.AsyncClient(timeout=15, verify=False) as client:
            r = await client.get(f"{CLOB_API}/book", params={"token_id": token_id})
            if r.status_code != 200:
                raise HTTPException(status_code=r.status_code, detail=f"CLOB API error: {r.text[:500]}")
            return r.json()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=str(e))


# ─── Authenticated endpoints (need API key) ───

async def _require_creds(db) -> dict:
    """Get creds or raise 400."""
    creds = await _get_polymarket_creds(db)
    if not creds["api_key"]:
        raise HTTPException(status_code=400, detail="Polymarket API key not configured. Go to Settings to add it.")
    return creds


class PlaceBetRequest(BaseModel):
    token_id: str
    side: str = "BUY"  # BUY or SELL
    price: float  # 0.01 - 0.99
    size: float  # Amount in USDC


@router.post("/bet")
async def place_bet(body: PlaceBetRequest, db: AsyncIOMotorDatabase = Depends(get_mongodb)):
    """Place a bet (limit order) on Polymarket."""
    creds = await _require_creds(db)
    if body.price < 0.01 or body.price > 0.99:
        raise HTTPException(status_code=400, detail="Price must be between 0.01 and 0.99")
    if body.size <= 0:
        raise HTTPException(status_code=400, detail="Size must be positive")

    order = {
        "tokenID": body.token_id,
        "side": body.side.upper(),
        "price": str(body.price),
        "size": str(body.size),
        "type": "GTC",  # Good Till Cancel
    }
    try:
        async with httpx.AsyncClient(timeout=30, verify=False) as client:
            r = await client.post(
                f"{CLOB_API}/order",
                json=order,
                headers=_clob_headers(creds),
            )
            if r.status_code not in (200, 201):
                raise HTTPException(status_code=r.status_code, detail=f"Order failed: {r.text[:500]}")
            result = r.json()

            # Save to local history
            await _save_bet_record(db, body, result)
            return result
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/positions")
async def get_positions(db: AsyncIOMotorDatabase = Depends(get_mongodb)):
    """Get current open positions / balances."""
    creds = await _require_creds(db)
    try:
        async with httpx.AsyncClient(timeout=15, verify=False) as client:
            r = await client.get(
                f"{CLOB_API}/positions",
                headers=_clob_headers(creds),
            )
            if r.status_code != 200:
                raise HTTPException(status_code=r.status_code, detail=f"API error: {r.text[:500]}")
            return r.json()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/orders")
async def get_orders(
    status: Optional[str] = Query(None, description="all, live, matched"),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Get order history from CLOB API."""
    creds = await _require_creds(db)
    params = {}
    if status:
        params["status"] = status
    try:
        async with httpx.AsyncClient(timeout=15, verify=False) as client:
            r = await client.get(
                f"{CLOB_API}/orders",
                headers=_clob_headers(creds),
                params=params,
            )
            if r.status_code != 200:
                raise HTTPException(status_code=r.status_code, detail=f"API error: {r.text[:500]}")
            return r.json()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/balance")
async def get_balance(db: AsyncIOMotorDatabase = Depends(get_mongodb)):
    """Get USDC balance."""
    creds = await _require_creds(db)
    try:
        async with httpx.AsyncClient(timeout=15, verify=False) as client:
            r = await client.get(
                f"{CLOB_API}/balance",
                headers=_clob_headers(creds),
            )
            if r.status_code != 200:
                raise HTTPException(status_code=r.status_code, detail=f"API error: {r.text[:500]}")
            return r.json()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=str(e))


# ─── Local bet history (MongoDB) ───

@router.get("/history")
async def bet_history(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Get local bet history stored in MongoDB."""
    col = db["addon_polymarket_bets"]
    total = await col.count_documents({})
    cursor = col.find({}).sort("created_at", -1).skip(offset).limit(limit)
    items = []
    async for doc in cursor:
        doc["id"] = str(doc.pop("_id"))
        items.append(doc)
    return {"items": items, "total": total}


@router.get("/history/stats")
async def bet_stats(db: AsyncIOMotorDatabase = Depends(get_mongodb)):
    """Get betting stats — total bets, wins, losses, profit."""
    col = db["addon_polymarket_bets"]
    total = await col.count_documents({})
    won = await col.count_documents({"result": "won"})
    lost = await col.count_documents({"result": "lost"})
    pending = await col.count_documents({"result": {"$in": [None, "pending"]}})

    pipeline = [
        {"$match": {"result": {"$in": ["won", "lost"]}}},
        {"$group": {"_id": None, "total_profit": {"$sum": "$profit"}, "total_invested": {"$sum": "$size"}}},
    ]
    agg = await col.aggregate(pipeline).to_list(1)
    profit = agg[0]["total_profit"] if agg else 0
    invested = agg[0]["total_invested"] if agg else 0

    return {
        "total_bets": total,
        "won": won,
        "lost": lost,
        "pending": pending,
        "total_profit": round(profit, 2),
        "total_invested": round(invested, 2),
        "win_rate": round(won / (won + lost) * 100, 1) if (won + lost) > 0 else 0,
    }


async def _save_bet_record(db, body: PlaceBetRequest, api_result: dict):
    """Save bet to local MongoDB for tracking."""
    col = db["addon_polymarket_bets"]
    await col.insert_one({
        "token_id": body.token_id,
        "side": body.side,
        "price": body.price,
        "size": body.size,
        "order_id": api_result.get("orderID") or api_result.get("id"),
        "result": "pending",
        "profit": 0,
        "api_response": api_result,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })


# ─── Manual result recording ───

class RecordResultRequest(BaseModel):
    result: str  # "won" or "lost"
    profit: float = 0


@router.patch("/history/{bet_id}")
async def record_bet_result(
    bet_id: str,
    body: RecordResultRequest,
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Record whether a bet was won or lost."""
    from bson import ObjectId
    col = db["addon_polymarket_bets"]
    r = await col.update_one(
        {"_id": ObjectId(bet_id)},
        {"$set": {"result": body.result, "profit": body.profit}},
    )
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Bet not found")
    return {"message": "Result recorded"}


# ─── AI Betting ─────────────────────────────────────────────

RARE_EVENTS_KEYWORDS = [
    "election", "president", "presidential", "vote", "governor", "senate",
    "congress", "prime minister", "parliament", "referendum", "nominee",
    "bitcoin", "btc", "ethereum", "eth", "crypto", "solana", "defi",
    "crash", "correction", "bear market", "bull market",
    "war", "invasion", "nuclear", "sanctions", "coup", "crisis", "conflict",
    "military", "nato", "missile", "ceasefire", "peace",
    "impeach", "resign", "assassination", "indictment", "arrest", "conviction",
    "earthquake", "hurricane", "tsunami", "pandemic", "outbreak", "wildfire",
    "recession", "default", "collapse", "bankruptcy",
    "tariff", "ban", "embargo", "trade war",
    "fed ", "interest rate", "inflation", "gdp", "unemployment",
    "spacex", "mars", "ai regulation", "tiktok",
]

STRATEGY_KEYWORDS = {
    "rare_events_micro": RARE_EVENTS_KEYWORDS,
}


class AiBettingAnalyzeRequest(BaseModel):
    strategy: str = "rare_events_micro"
    agent_id: Optional[str] = None
    default_amount: float = 1.0
    max_odds: float = 0.35
    min_multiplier: float = 2.5


class SessionBetsUpdateRequest(BaseModel):
    bets: List[dict]
    default_amount: Optional[float] = None
    min_multiplier: Optional[float] = None


@router.post("/ai-betting/analyze")
async def ai_betting_analyze(
    body: AiBettingAnalyzeRequest,
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Fetch active events, filter by strategy keywords, build betting session."""
    keywords = STRATEGY_KEYWORDS.get(body.strategy, RARE_EVENTS_KEYWORDS)

    # 1. Fetch events from Gamma API (multiple pages)
    all_events = []
    for offset in range(0, 500, 100):
        try:
            async with httpx.AsyncClient(timeout=30, verify=False) as client:
                r = await client.get(f"{GAMMA_API}/events", params={
                    "limit": 100, "offset": offset,
                    "active": "true", "closed": "false",
                })
                if r.status_code == 200:
                    batch = r.json()
                    if not batch:
                        break
                    all_events.extend(batch)
                else:
                    break
        except Exception as exc:
            logger.warning("Gamma fetch page offset=%s failed: %s", offset, exc)
            break

    logger.info("AI Betting: fetched %d events from Gamma", len(all_events))

    # 2. Filter by strategy keywords
    filtered_events = []
    for ev in all_events:
        text = f"{ev.get('title', '')} {ev.get('description', '')}".lower()
        for m in ev.get("markets", []):
            text += f" {m.get('question', '')}".lower()
        if any(kw in text for kw in keywords):
            filtered_events.append(ev)

    logger.info("AI Betting: %d events match strategy '%s'", len(filtered_events), body.strategy)

    # 3. Build bet options — pick the rare (low-probability) side of each market
    bets = []
    bet_num = 0
    for ev in filtered_events:
        for m in ev.get("markets", []):
            if not m.get("active", True):
                continue
            prices = _parse_outcome_prices(m.get("outcomePrices"))
            tokens = _parse_token_ids(m.get("clobTokenIds"))
            yes_p = prices.get("outcome_yes")
            no_p = prices.get("outcome_no")
            if yes_p is None or no_p is None:
                continue

            sides = []
            if 0.005 < yes_p <= body.max_odds:
                mult = round(1 / yes_p, 2)
                if mult >= body.min_multiplier:
                    sides.append({
                        "side": "YES", "odds": yes_p,
                        "token_id": tokens.get("token_id_yes"),
                        "payout_multiplier": mult,
                    })
            if 0.005 < no_p <= body.max_odds:
                mult = round(1 / no_p, 2)
                if mult >= body.min_multiplier:
                    sides.append({
                        "side": "NO", "odds": no_p,
                        "token_id": tokens.get("token_id_no"),
                        "payout_multiplier": mult,
                    })

            for s in sides:
                bet_num += 1
                bets.append({
                    "number": bet_num,
                    "event_title": ev.get("title", ""),
                    "market_id": m.get("id"),
                    "market_question": m.get("question", ""),
                    "side": s["side"],
                    "odds": s["odds"],
                    "token_id": s["token_id"],
                    "payout_multiplier": s["payout_multiplier"],
                    "amount": body.default_amount,
                    "expected_payout": round(body.default_amount * s["payout_multiplier"], 2),
                    "selected": True,
                })

    # 4. Create session document
    session_id = str(uuid.uuid4())
    session = {
        "id": session_id,
        "strategy": body.strategy,
        "agent_id": body.agent_id,
        "default_amount": body.default_amount,
        "max_odds": body.max_odds,
        "min_multiplier": body.min_multiplier,
        "bets": bets,
        "total_events": len(filtered_events),
        "total_bets": len(bets),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "draft",
    }
    await db["polymarket_sessions"].insert_one({**session, "_id": session_id})

    logger.info("AI Betting: session %s created with %d bets", session_id, len(bets))
    return session


@router.get("/ai-betting/sessions")
async def list_ai_betting_sessions(
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """List past AI betting sessions (newest first)."""
    cursor = db["polymarket_sessions"].find().sort("created_at", -1).limit(50)
    sessions = []
    async for doc in cursor:
        doc.pop("_id", None)
        # Return summary without full bets array
        doc["bets_count"] = len(doc.get("bets", []))
        doc.pop("bets", None)
        sessions.append(doc)
    return sessions


@router.get("/ai-betting/sessions/{session_id}")
async def get_ai_betting_session(
    session_id: str,
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Get a single AI betting session with all bets."""
    doc = await db["polymarket_sessions"].find_one({"id": session_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Session not found")
    doc.pop("_id", None)
    return doc


@router.patch("/ai-betting/sessions/{session_id}")
async def update_session_bets(
    session_id: str,
    body: SessionBetsUpdateRequest,
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Update bets selection/amounts in a session."""
    update_fields = {"bets": body.bets}
    if body.default_amount is not None:
        update_fields["default_amount"] = body.default_amount
    if body.min_multiplier is not None:
        update_fields["min_multiplier"] = body.min_multiplier
    r = await db["polymarket_sessions"].update_one(
        {"id": session_id},
        {"$set": update_fields},
    )
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Session updated"}


@router.delete("/ai-betting/sessions/{session_id}")
async def delete_ai_betting_session(
    session_id: str,
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Delete an AI betting session."""
    r = await db["polymarket_sessions"].delete_one({"id": session_id})
    if r.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Session deleted"}


@router.post("/ai-betting/sessions/{session_id}/place")
async def place_session_bets(
    session_id: str,
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Place all selected bets in a session via CLOB API."""
    doc = await db["polymarket_sessions"].find_one({"id": session_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Session not found")

    creds = await _get_polymarket_creds(db)
    if not creds["api_key"]:
        raise HTTPException(status_code=400, detail="Polymarket API credentials not configured")

    headers = _clob_headers(creds)
    results = []

    for bet in doc.get("bets", []):
        if not bet.get("selected") or not bet.get("token_id"):
            continue
        try:
            async with httpx.AsyncClient(timeout=30, verify=False) as client:
                r = await client.post(f"{CLOB_API}/order", headers=headers, json={
                    "tokenID": bet["token_id"],
                    "side": "BUY",
                    "price": str(bet["odds"]),
                    "size": str(bet["amount"]),
                })
                success = r.status_code in (200, 201)
                detail = r.json() if success else r.text[:300]
                results.append({
                    "bet_number": bet["number"],
                    "success": success,
                    "detail": detail,
                })
                # Also save to bet history
                if success:
                    await db["addon_polymarket_bets"].insert_one({
                        "token_id": bet["token_id"],
                        "side": bet["side"],
                        "price": bet["odds"],
                        "size": bet["amount"],
                        "order_id": detail.get("orderID") or detail.get("id"),
                        "result": "pending",
                        "profit": 0,
                        "session_id": session_id,
                        "api_response": detail,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    })
        except Exception as exc:
            results.append({
                "bet_number": bet["number"],
                "success": False,
                "detail": str(exc),
            })

    placed = len([r for r in results if r["success"]])
    failed = len([r for r in results if not r["success"]])

    # Update session status
    new_status = "placed" if failed == 0 else ("partial" if placed > 0 else "failed")

    # Mark successfully placed bets in the session document
    placed_numbers = {r["bet_number"] for r in results if r["success"]}
    if placed_numbers:
        bets = doc.get("bets", [])
        for bet in bets:
            if bet.get("number") in placed_numbers:
                bet["placed"] = True
                bet["selected"] = False
        update_fields = {"status": new_status, "place_results": results, "bets": bets}
    else:
        update_fields = {"status": new_status, "place_results": results}

    await db["polymarket_sessions"].update_one(
        {"id": session_id},
        {"$set": update_fields},
    )

    return {"placed": placed, "failed": failed, "results": results}


# ─── Agent Analysis ──────────────────────────────────────────

class AgentAnalyzeRequest(BaseModel):
    agent_id: str
    bet_numbers: List[int] = []  # which bets to analyze; empty = all selected
    total_budget: float = 100.0
    bet_amount: float = 1.0
    min_multiplier: float = 2.5


@router.post("/ai-betting/sessions/{session_id}/agent-analyze")
async def agent_analyze_bets(
    session_id: str,
    body: AgentAnalyzeRequest,
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Send selected bets to the agent for analysis. Agent returns verdict + reasoning."""
    from app.services.agent_chat_engine import AgentChatEngine

    doc = await db["polymarket_sessions"].find_one({"id": session_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Session not found")

    bets = doc.get("bets", [])
    # Filter to requested bets, excluding already-placed ones
    if body.bet_numbers:
        to_analyze = [b for b in bets if b["number"] in body.bet_numbers and not b.get("placed")]
    else:
        to_analyze = [b for b in bets if b.get("selected") and not b.get("placed")]

    if not to_analyze:
        raise HTTPException(status_code=400, detail="No bets selected for analysis")

    # Budget / selection math
    max_picks = int(body.total_budget / body.bet_amount) if body.bet_amount > 0 else len(to_analyze)
    max_picks = min(max_picks, len(to_analyze))

    # Build prompt for agent
    bets_text = ""
    for b in to_analyze:
        bets_text += (
            f"#{b['number']}. \"{b['event_title']}\" — {b['market_question']}\n"
            f"   Side: {b['side']}, Odds: {b['odds']*100:.1f}% (x{b['payout_multiplier']})\n\n"
        )

    prompt = f"""You are a professional prediction-market analyst. Your job is to pick the BEST bets from the list below.

CONTEXT:
- Total budget: ${body.total_budget:.2f}
- Bet amount per position: ${body.bet_amount:.2f}
- Maximum number of bets I can place: {max_picks}
- Minimum payout multiplier required: x{body.min_multiplier}
- Number of candidates: {len(to_analyze)}

YOUR TASK:
From {len(to_analyze)} candidates, select the TOP {max_picks} bets that have the highest realistic probability of winning.
Mark your top {max_picks} picks as "green", mark borderline/uncertain ones as "yellow", and mark the rest as "red" (do NOT bet).

Prioritize:
1. Events where the market underestimates the real probability (value bets)
2. Higher payout multipliers at reasonable likelihood
3. Recent news, geopolitical context, historical patterns
4. Avoid correlated bets (don't pick 5 bets on the same event)

Respond ONLY with valid JSON — an array of objects, one per bet. No markdown, no explanation outside JSON.
Each object must have exactly these fields:
- "number": the bet number (integer)
- "verdict": "green", "yellow", or "red"
- "reasoning": 1-2 sentence explanation (string)

Here are the bets:

{bets_text}

Respond with JSON array:"""

    engine = AgentChatEngine(db)
    try:
        result = await engine.generate_full(
            agent_id=body.agent_id,
            user_input=prompt,
            history=[],
            session_id=session_id,
            load_skills=False,
            load_protocols=False,
            enable_thinking_log=True,
            max_skill_iterations=0,
        )
    except Exception as exc:
        logger.error("Agent analysis failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Agent call failed: {exc}")

    # Parse response — extract JSON array
    raw = result.content.strip()
    # Try to find JSON array in response
    import re as _re
    m = _re.search(r'\[.*\]', raw, _re.DOTALL)
    if not m:
        logger.warning("Agent returned non-JSON: %s", raw[:500])
        raise HTTPException(status_code=422, detail="Agent did not return valid JSON. Raw response: " + raw[:500])

    try:
        verdicts = json.loads(m.group(0))
    except json.JSONDecodeError:
        raise HTTPException(status_code=422, detail="Failed to parse agent JSON: " + m.group(0)[:500])

    # Build lookup
    verdict_map = {}
    for v in verdicts:
        if isinstance(v, dict) and "number" in v:
            verdict_map[v["number"]] = {
                "verdict": v.get("verdict", "yellow"),
                "reasoning": v.get("reasoning", ""),
            }

    # Apply verdicts to session bets
    for b in bets:
        v = verdict_map.get(b["number"])
        if v:
            b["agent_verdict"] = v["verdict"]
            b["agent_reasoning"] = v["reasoning"]
            if v["verdict"] == "red":
                b["selected"] = False

    # Save back
    thinking_log_id = getattr(result, 'thinking_log_id', None)
    update_fields = {"bets": bets, "agent_analyzed": True}
    if thinking_log_id:
        # Append to analysis_logs list
        await db["polymarket_sessions"].update_one(
            {"id": session_id},
            {
                "$set": update_fields,
                "$push": {"analysis_logs": {
                    "thinking_log_id": thinking_log_id,
                    "agent_id": body.agent_id,
                    "bets_analyzed": len(to_analyze),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "verdicts_summary": {
                        "green": len([v for v in verdict_map.values() if v["verdict"] == "green"]),
                        "yellow": len([v for v in verdict_map.values() if v["verdict"] == "yellow"]),
                        "red": len([v for v in verdict_map.values() if v["verdict"] == "red"]),
                    },
                }},
            },
        )
    else:
        await db["polymarket_sessions"].update_one(
            {"id": session_id},
            {"$set": update_fields},
        )

    return {
        "analyzed": len(verdict_map),
        "green": len([v for v in verdict_map.values() if v["verdict"] == "green"]),
        "yellow": len([v for v in verdict_map.values() if v["verdict"] == "yellow"]),
        "red": len([v for v in verdict_map.values() if v["verdict"] == "red"]),
        "verdicts": verdict_map,
        "thinking_log_id": thinking_log_id,
    }


@router.get("/ai-betting/sessions/{session_id}/thinking-logs")
async def get_session_thinking_logs(
    session_id: str,
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Get analysis thinking logs for a session."""
    doc = await db["polymarket_sessions"].find_one({"id": session_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Session not found")
    return doc.get("analysis_logs", [])


@router.get("/ai-betting/thinking-logs/{log_id}")
async def get_thinking_log_detail(
    log_id: str,
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Get thinking log detail with all steps."""
    log_doc = await db["thinking_logs"].find_one({"_id": log_id})
    if not log_doc:
        raise HTTPException(status_code=404, detail="Thinking log not found")
    log_doc["id"] = log_doc.pop("_id")

    # Get steps
    steps_cursor = db["thinking_steps"].find({"thinking_log_id": log_id}).sort("step_order", 1)
    steps = []
    async for s in steps_cursor:
        s["id"] = s.pop("_id")
        steps.append(s)

    log_doc["steps"] = steps
    return log_doc
