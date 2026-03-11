import httpx
import os

CLOB_API = "https://clob.polymarket.com"

async def execute(token_id, price, size, side="BUY"):
    api_key = os.environ.get("POLYMARKET_API_KEY", "")
    api_secret = os.environ.get("POLYMARKET_API_SECRET", "")
    passphrase = os.environ.get("POLYMARKET_PASSPHRASE", "")
    if not api_key:
        return {"error": "Polymarket API key not configured. Go to Settings to add it."}
    if not token_id:
        return {"error": "token_id is required"}
    price = float(price)
    size = float(size)
    if price < 0.01 or price > 0.99:
        return {"error": "Price must be between 0.01 and 0.99"}
    if size <= 0:
        return {"error": "Size must be positive"}

    headers = {
        "Content-Type": "application/json",
        "POLY_API_KEY": api_key,
        "POLY_API_SECRET": api_secret,
        "POLY_PASSPHRASE": passphrase,
    }
    order = {
        "tokenID": token_id,
        "side": side.upper(),
        "price": str(price),
        "size": str(size),
        "type": "GTC",
    }
    try:
        async with httpx.AsyncClient(timeout=30, verify=False) as client:
            r = await client.post(f"{CLOB_API}/order", json=order, headers=headers)
            if r.status_code not in (200, 201):
                return {"error": f"Order failed ({r.status_code}): {r.text[:500]}"}
            result = r.json()
            return {
                "success": True,
                "order_id": result.get("orderID") or result.get("id"),
                "token_id": token_id,
                "side": side,
                "price": price,
                "size": size,
                "status": result.get("status", "submitted"),
                "raw": result,
            }
    except Exception as e:
        return {"error": f"Failed to place bet: {e}"}
