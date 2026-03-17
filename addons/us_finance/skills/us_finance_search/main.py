"""US Finance: search skill for agent use."""


async def execute(query: str = "", section: str = "", limit: int = 20):
    """Search US finance data across all collections."""
    from app.database import get_mongodb

    db = get_mongodb()
    results = []

    sections_to_search = []
    if section:
        sections_to_search = [section]
    else:
        sections_to_search = ["news", "real_estate", "oil", "programs", "taxation"]

    for sec in sections_to_search:
        if sec == "news":
            items = await _search_collection(db, "usf_news", query, limit)
            for item in items:
                results.append(
                    f"[NEWS] {item.get('label', '')} = {item.get('latest_value', 'N/A')}{item.get('unit', '')} "
                    f"(as of {item.get('latest_date', '')}, source: {item.get('source', '')})"
                )

        elif sec == "real_estate":
            items = await _search_collection(db, "usf_real_estate", query, limit)
            for item in items:
                hist = item.get("history", [])
                trend = ""
                if len(hist) >= 2:
                    try:
                        v1 = float(hist[0]["value"])
                        v2 = float(hist[1]["value"])
                        pct = ((v1 - v2) / v2 * 100) if v2 != 0 else 0
                        trend = f" (trend: {'+' if pct >= 0 else ''}{pct:.1f}%)"
                    except (ValueError, KeyError):
                        pass
                results.append(
                    f"[REAL ESTATE] {item.get('label', '')} = {item.get('latest_value', 'N/A')} "
                    f"(as of {item.get('latest_date', '')}){trend}"
                )

        elif sec == "oil":
            items = await _search_collection(db, "usf_oil", query, limit)
            for item in items:
                results.append(
                    f"[OIL/ENERGY] {item.get('label', '')} = {item.get('latest_value', 'N/A')} {item.get('unit', '')} "
                    f"(as of {item.get('latest_date', '')})"
                )

        elif sec == "programs":
            items = await _search_collection(db, "usf_programs", query, limit)
            for item in items:
                desc = (item.get("description") or "")[:200]
                if len(item.get("description", "")) > 200:
                    desc += "..."
                url = item.get("url", "")
                url_part = f" | URL: {url}" if url else ""
                results.append(
                    f"[PROGRAM] {item.get('title', '')} — {item.get('state', 'National')} "
                    f"({item.get('source', '')})\n  {desc}{url_part}"
                )

        elif sec == "taxation":
            # Taxation is static data from the routes, search the backend endpoint
            try:
                from addons.us_finance.backend.routes import US_STATES_TAX, US_STATES_CORP_TAX
                q_lower = query.lower() if query else ""
                for state in US_STATES_TAX:
                    if not q_lower or q_lower in state["state"].lower() or q_lower in state["abbr"].lower():
                        no_inc = " [NO INCOME TAX]" if state["no_income_tax"] else ""
                        notes = (" — " + state["notes"]) if state.get("notes") else ""
                        results.append(
                            f"[TAX-INDIVIDUAL] {state['state']} ({state['abbr']}){no_inc}: "
                            f"Income: {state['income_tax']}, Sales: {state['sales_tax']}, "
                            f"Property: {state['property_tax']}{notes}"
                        )
                for state in US_STATES_CORP_TAX:
                    if not q_lower or q_lower in state["state"].lower() or q_lower in state["abbr"].lower():
                        notes = (" — " + state["notes"]) if state.get("notes") else ""
                        results.append(
                            f"[TAX-CORPORATE] {state['state']} ({state['abbr']}): "
                            f"Corp: {state['corp_tax']}, Franchise: {state['franchise_tax']}, "
                            f"LLC: {state['llc_fee']}{notes}"
                        )
            except ImportError:
                results.append("[TAXATION] Tax data module not available")

    if not results:
        # Check if we have any data
        total = 0
        for col_name in ["usf_news", "usf_real_estate", "usf_oil", "usf_programs"]:
            total += await db[col_name].count_documents({})
        if total == 0:
            return (
                "No US finance data available. The US Finance addon needs to scrape data first. "
                "Ask the user to click 'Scrape All' in the US Finance page."
            )
        return f"No items found matching query='{query}', section='{section}'. There are {total} total items."

    header = f"Found {len(results)} US finance results"
    if query:
        header += f" for '{query}'"
    if section:
        header += f" in section '{section}'"
    header += ":"

    return header + "\n\n" + "\n\n".join(results[:limit])


async def _search_collection(db, collection_name: str, query: str, limit: int) -> list:
    """Search a MongoDB collection by text or regex."""
    col = db[collection_name]
    mongo_query = {}

    if query:
        regex = {"$regex": query, "$options": "i"}
        mongo_query["$or"] = [
            {"label": regex},
            {"title": regex},
            {"description": regex},
            {"series_id": regex},
            {"state": regex},
        ]

    try:
        items = await col.find(mongo_query).sort("scraped_at", -1).limit(limit).to_list(length=limit)
    except Exception:
        items = []

    return items
