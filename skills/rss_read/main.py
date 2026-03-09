import httpx
import xml.etree.ElementTree as ET

async def execute(url, limit=20):
    """Read and parse RSS/Atom feeds."""
    async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
        resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0 (compatible; bot/1.0)"})
        resp.raise_for_status()
    root = ET.fromstring(resp.text)
    entries = []
    # RSS 2.0
    for item in root.iter("item"):
        entry = {}
        for field in ("title", "link", "description", "pubDate", "author", "guid"):
            el = item.find(field)
            if el is not None and el.text:
                entry[field] = el.text.strip()
        if "description" in entry:
            entry["description"] = entry["description"][:500]
        entries.append(entry)
    # Atom
    if not entries:
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        for item in root.findall(".//atom:entry", ns):
            entry = {}
            t = item.find("atom:title", ns)
            if t is not None and t.text:
                entry["title"] = t.text.strip()
            link = item.find("atom:link", ns)
            if link is not None:
                entry["link"] = link.get("href", "")
            s = item.find("atom:summary", ns)
            if s is not None and s.text:
                entry["description"] = s.text.strip()[:500]
            u = item.find("atom:updated", ns)
            if u is not None and u.text:
                entry["pubDate"] = u.text.strip()
            entries.append(entry)
    return {"entries": entries[:limit], "total": len(entries), "feed_url": url}
