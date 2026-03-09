import httpx
import re

async def execute(query, limit=10, region="wt-wt"):
    """Search the internet via DuckDuckGo HTML."""
    url = "https://html.duckduckgo.com/html/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:109.0) Gecko/20100101 Firefox/115.0"}
    data = {"q": query, "kl": region}
    async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
        resp = await client.post(url, data=data, headers=headers)
        resp.raise_for_status()
    html = resp.text
    results = []
    for m in re.finditer(
        r'<a rel="nofollow" class="result__a" href="([^"]*)"[^>]*>(.*?)</a>',
        html, re.DOTALL
    ):
        href, title = m.group(1), re.sub(r"<[^>]+>", "", m.group(2)).strip()
        snippet = ""
        snip = re.search(r'<a class="result__snippet"[^>]*>(.*?)</a>', html[m.end():m.end()+2000], re.DOTALL)
        if snip:
            snippet = re.sub(r"<[^>]+>", "", snip.group(1)).strip()
        results.append({"title": title, "url": href, "snippet": snippet})
        if len(results) >= limit:
            break
    return {"results": results, "total": len(results), "query": query}
