import httpx
import os

CLOB_API = "https://clob.polymarket.com"

async def execute():
    api_key = os.environ.get("POLYMARKET_API_KEY", "")
    api_secret = os.environ.get("POLYMARKET_API_SECRET", "")
    passphrase = os.environ.get("POLYMARKET_PASSPHRASE", "")
    if not api_key:
        return {"error": "Polymarket API key not configured. Go to Settings to add it."}
    headers = {
        "Content-Type": "application/json",
        "POLY_API_KEY": api_key,
        "POLY_API_SECRET": api_secret,
        "POLY_PASSPHRASE": passphrase,
    }
    try:
        async with httpx.AsyncClient(timeout=15, verify=False) as client:
            r = await client.get(f"{CLOB_API}/balance", headers=headers)
            if r.status_code != 200:
                return {"error": f"API error {r.status_code}: {r.text[:500]}"}
            return r.json()
    except Exception as e:
        return {"error": f"Failed to fetch balance: {e}"}
