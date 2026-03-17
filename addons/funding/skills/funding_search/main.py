"""
Funding Search skill — searches VC firms, investors, and SMB programs in MongoDB.
"""

import re


async def run(params: dict, context: dict = None) -> dict:
    query = (params.get("query") or "").strip()
    section = (params.get("section") or "").strip().lower()
    limit = int(params.get("limit", 20))

    if not query:
        return {"error": "Please provide a search query."}

    try:
        from app.database import get_mongodb
        db = get_mongodb()
    except Exception as e:
        return {"error": f"Database connection failed: {e}"}

    regex = {"$regex": re.escape(query), "$options": "i"}
    results = []

    # Search VC firms
    if not section or section == "vc":
        cursor = db["funding_vc_firms"].find({
            "$or": [{"name": regex}, {"notable_investments": regex}, {"location": regex}]
        }).limit(limit)
        async for doc in cursor:
            sectors = ", ".join(doc.get("sectors", []))
            stages = ", ".join(doc.get("stages", []))
            results.append({
                "type": "vc_firm",
                "name": doc.get("name", ""),
                "firm_type": doc.get("type", ""),
                "location": doc.get("location", ""),
                "aum": doc.get("aum", ""),
                "stages": stages,
                "sectors": sectors,
                "website": doc.get("website", ""),
            })

    # Search investors
    if not section or section == "investors":
        cursor = db["funding_investors"].find({
            "$or": [{"name": regex}, {"firm": regex}, {"bio": regex}]
        }).limit(limit)
        async for doc in cursor:
            results.append({
                "type": "investor",
                "name": doc.get("name", ""),
                "investor_type": doc.get("investor_type", ""),
                "firm": doc.get("firm", ""),
                "location": doc.get("location", ""),
                "sectors": ", ".join(doc.get("sectors", [])),
            })

    # Search SMB programs
    if not section or section == "smb":
        cursor = db["funding_smb_programs"].find({
            "$or": [{"name": regex}, {"description": regex}, {"agency": regex}]
        }).limit(limit)
        async for doc in cursor:
            results.append({
                "type": "smb_program",
                "name": doc.get("name", ""),
                "program_type": doc.get("type", ""),
                "max_amount": doc.get("max_amount"),
                "agency": doc.get("agency", ""),
                "description": (doc.get("description") or "")[:200],
            })

    if not results:
        return {"result": f"No funding data found matching '{query}'."}

    lines = []
    for r in results:
        if r["type"] == "vc_firm":
            lines.append(f"- [VC] {r['name']} ({r['firm_type']}) — {r['location']}, AUM: ${r['aum']}, Stages: {r['stages']}")
        elif r["type"] == "investor":
            lines.append(f"- [Investor] {r['name']} ({r['investor_type']}) at {r['firm']} — {r['location']}")
        else:
            amount = f" up to ${r['max_amount']:,.0f}" if r.get("max_amount") else ""
            lines.append(f"- [SMB] {r['name']} ({r['program_type']}){amount} — {r['agency']}")

    summary = f"Found {len(results)} results:\n" + "\n".join(lines)
    return {"result": summary, "items": results, "total": len(results)}
