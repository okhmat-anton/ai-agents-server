import httpx
import json

GAMMA_API = "https://gamma-api.polymarket.com"


def _parse_prices(raw):
    """Parse outcomePrices — may be JSON string or list."""
    if not raw:
        return {"yes_price": None, "no_price": None}
    try:
        prices = json.loads(raw) if isinstance(raw, str) else raw
        return {
            "yes_price": float(prices[0]) if len(prices) > 0 and prices[0] is not None else None,
            "no_price": float(prices[1]) if len(prices) > 1 and prices[1] is not None else None,
        }
    except (json.JSONDecodeError, TypeError, ValueError, IndexError):
        return {"yes_price": None, "no_price": None}


def _parse_token_ids(raw):
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

async def execute(search=None, limit=20, active=True, closed=False):
    params = {
        "limit": min(int(limit), 100),
        "offset": 0,
        "active": str(active).lower(),
        "closed": str(closed).lower(),
    }
    if search:
        params["tag"] = search
    try:
        async with httpx.AsyncClient(timeout=15, verify=False) as client:
            r = await client.get(f"{GAMMA_API}/events", params=params)
            if r.status_code != 200:
                return {"error": f"Gamma API error {r.status_code}: {r.text[:300]}"}
            events = r.json()
            result = []
            for ev in events:
                markets = ev.get("markets", [])
                result.append({
                    "title": ev.get("title"),
                    "slug": ev.get("slug"),
                    "active": ev.get("active"),
                    "volume": ev.get("volume"),
                    "liquidity": ev.get("liquidity"),
                    "markets": [
                        {
                            "question": m.get("question"),
                            **_parse_prices(m.get("outcomePrices")),
                            "volume": m.get("volume"),
                            **_parse_token_ids(m.get("clobTokenIds")),
                        }
                        for m in markets[:5]
                    ],
                })
            return {"events": result, "count": len(result)}
    except Exception as e:
        return {"error": f"Failed to fetch events: {e}"}
