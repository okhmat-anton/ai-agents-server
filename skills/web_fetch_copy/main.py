import httpx
async def execute(url, method='GET', **kwargs):
    async with httpx.AsyncClient() as c:
        r = await getattr(c, method.lower())(url, **kwargs)
        return {'status': r.status_code, 'text': r.text[:5000]}