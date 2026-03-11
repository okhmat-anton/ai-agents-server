import httpx

CLOB_API = "https://clob.polymarket.com"

async def execute(token_id):
    if not token_id:
        return {"error": "token_id is required"}
    try:
        async with httpx.AsyncClient(timeout=15, verify=False) as client:
            r = await client.get(f"{CLOB_API}/book", params={"token_id": token_id})
            if r.status_code != 200:
                return {"error": f"CLOB API error {r.status_code}: {r.text[:300]}"}
            book = r.json()
            bids = book.get("bids", [])
            asks = book.get("asks", [])
            best_bid = float(bids[0]["price"]) if bids else None
            best_ask = float(asks[0]["price"]) if asks else None
            spread = round(best_ask - best_bid, 4) if best_bid and best_ask else None
            return {
                "token_id": token_id,
                "best_bid": best_bid,
                "best_ask": best_ask,
                "spread": spread,
                "bid_depth": len(bids),
                "ask_depth": len(asks),
                "top_bids": [{"price": b["price"], "size": b["size"]} for b in bids[:5]],
                "top_asks": [{"price": a["price"], "size": a["size"]} for a in asks[:5]],
            }
    except Exception as e:
        return {"error": f"Failed to fetch orderbook: {e}"}
