"""
Grants Search skill — searches stored grant data in MongoDB.
"""

import re
from datetime import datetime, timezone


async def run(params: dict, context: dict = None) -> dict:
    query = (params.get("query") or "").strip()
    category = (params.get("category") or "").strip()
    limit = int(params.get("limit", 20))

    if not query and not category:
        return {"error": "Please provide a query or category to search grants."}

    try:
        from app.database import get_mongodb
        db = get_mongodb()
    except Exception as e:
        return {"error": f"Database connection failed: {e}"}

    mongo_query = {}

    if query:
        regex = {"$regex": re.escape(query), "$options": "i"}
        mongo_query["$or"] = [
            {"title": regex},
            {"description": regex},
            {"agency": regex},
            {"category": regex},
        ]

    if category:
        mongo_query["category"] = {"$regex": re.escape(category), "$options": "i"}

    results = []
    cursor = db["grants_items"].find(mongo_query).sort("close_date", 1).limit(limit)

    async for doc in cursor:
        results.append({
            "title": doc.get("title", ""),
            "agency": doc.get("agency", ""),
            "category": doc.get("category", ""),
            "award_ceiling": doc.get("award_ceiling"),
            "close_date": doc.get("close_date"),
            "status": doc.get("status", ""),
            "description": (doc.get("description") or "")[:300],
            "url": doc.get("url", ""),
            "opportunity_number": doc.get("opportunity_number", ""),
        })

    if not results:
        search_desc = query or category
        return {"result": f"No grants found matching '{search_desc}'."}

    summary_lines = []
    for r in results:
        amount = f" — up to ${r['award_ceiling']:,.0f}" if r.get("award_ceiling") else ""
        deadline = f" (deadline: {r['close_date']})" if r.get("close_date") else ""
        summary_lines.append(f"- {r['title']}{amount}{deadline} [{r['agency']}]")

    summary = f"Found {len(results)} grants:\n" + "\n".join(summary_lines)

    return {
        "result": summary,
        "grants": results,
        "total": len(results),
    }
