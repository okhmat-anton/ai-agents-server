"""
Geopolitics Search skill — searches news articles and Pentagon open source data.
"""
import re
from datetime import datetime


async def run(params: dict, context: dict = None) -> dict:
    """Search geopolitics news and Pentagon open sources."""
    query = (params.get("query") or "").strip()
    source_type = (params.get("source_type") or "all").lower()
    limit = int(params.get("limit", 10))

    if not query:
        return {"success": False, "error": "Query parameter is required"}

    if limit < 1:
        limit = 1
    elif limit > 50:
        limit = 50

    try:
        from app.database import get_mongodb
        db = get_mongodb()
    except Exception as e:
        return {"success": False, "error": f"Database connection failed: {str(e)}"}

    keywords = [kw.strip().lower() for kw in re.split(r'[,\s]+', query) if kw.strip()]
    if not keywords:
        return {"success": False, "error": "No valid keywords found"}

    # Build text search filter
    regex_parts = [re.escape(kw) for kw in keywords]
    regex_pattern = "|".join(regex_parts)

    results = []

    # Search news articles
    if source_type in ("all", "news"):
        news_filter = {
            "$or": [
                {"title": {"$regex": regex_pattern, "$options": "i"}},
                {"summary": {"$regex": regex_pattern, "$options": "i"}},
                {"tags": {"$regex": regex_pattern, "$options": "i"}},
            ]
        }
        try:
            cursor = db.geopolitics_news.find(news_filter).sort("published_at", -1).limit(limit)
            async for doc in cursor:
                results.append({
                    "id": str(doc["_id"]),
                    "type": "news",
                    "title": doc.get("title", ""),
                    "url": doc.get("url", ""),
                    "source_name": doc.get("source_name", ""),
                    "category": doc.get("category", ""),
                    "summary": (doc.get("summary") or "")[:500],
                    "importance": doc.get("importance", "medium"),
                    "published_at": doc.get("published_at", ""),
                    "tags": doc.get("tags", []),
                })
        except Exception as e:
            pass  # collection may not exist yet

    # Search Pentagon items
    if source_type in ("all", "pentagon"):
        pentagon_filter = {
            "$or": [
                {"title": {"$regex": regex_pattern, "$options": "i"}},
                {"source_name": {"$regex": regex_pattern, "$options": "i"}},
            ]
        }
        try:
            cursor = db.geopolitics_pentagon.find(pentagon_filter).sort("published_at", -1).limit(limit)
            async for doc in cursor:
                results.append({
                    "id": str(doc["_id"]),
                    "type": "pentagon",
                    "title": doc.get("title", ""),
                    "url": doc.get("url", ""),
                    "source_name": doc.get("source_name", ""),
                    "source_type": doc.get("source_type", ""),
                    "published_at": doc.get("published_at", ""),
                })
        except Exception as e:
            pass

    # Sort combined results by date
    results.sort(key=lambda x: x.get("published_at", ""), reverse=True)
    results = results[:limit]

    return {
        "success": True,
        "query": query,
        "source_type": source_type,
        "total_results": len(results),
        "results": results,
        "searched_at": datetime.utcnow().isoformat(),
    }
