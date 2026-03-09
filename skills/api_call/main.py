import httpx

async def execute(url, method="GET", headers=None, body=None, auth_type=None, auth_value=None, timeout=30):
    """Make HTTP API calls with full control over headers, body, and authentication."""
    hdrs = dict(headers or {})
    if auth_type and auth_value:
        if auth_type == "bearer":
            hdrs["Authorization"] = f"Bearer {auth_value}"
        elif auth_type == "api_key":
            hdrs["X-API-Key"] = auth_value
        elif auth_type == "basic":
            import base64
            hdrs["Authorization"] = "Basic " + base64.b64encode(auth_value.encode()).decode()
    kwargs = {"headers": hdrs, "timeout": timeout}
    if body is not None:
        if isinstance(body, (dict, list)):
            kwargs["json"] = body
        else:
            kwargs["content"] = str(body)
    async with httpx.AsyncClient(follow_redirects=True) as client:
        resp = await getattr(client, method.lower())(url, **kwargs)
    try:
        resp_body = resp.json()
    except Exception:
        resp_body = resp.text[:5000]
    return {"status_code": resp.status_code, "headers": dict(resp.headers), "body": resp_body}
