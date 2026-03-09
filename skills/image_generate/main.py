import httpx
import os

async def execute(prompt, size="1024x1024", quality="standard", style="vivid"):
    """Generate images using DALL-E 3 API. Requires OPENAI_API_KEY."""
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return {"error": "OPENAI_API_KEY not set. Configure openai_api_key in system settings."}
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            "https://api.openai.com/v1/images/generations",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": "dall-e-3", "prompt": prompt, "n": 1, "size": size, "quality": quality, "style": style},
        )
        if resp.status_code != 200:
            return {"error": f"DALL-E API error ({resp.status_code}): {resp.text[:500]}"}
        data = resp.json()
    img = data.get("data", [{}])[0]
    return {"url": img.get("url", ""), "revised_prompt": img.get("revised_prompt", ""), "prompt": prompt}
