import httpx
import os
async def execute():
    api_key = os.environ.get('AKM_ADVISOR_API_KEY', '')
    base_url = os.environ.get('AKM_ADVISOR_URL', 'https://app.akm-advisor.com')
    if not api_key:
        return {'error': 'AKM Advisor API key not configured. Go to Settings to add it.'}
    headers = {'Authorization': f'Bearer {api_key}'}
    async with httpx.AsyncClient(timeout=20, verify=False) as client:
        r = await client.get(f'{base_url}/api/v1/data/projects?limit=100', headers=headers)
        if r.status_code != 200:
            return {'error': f'API error {r.status_code}: {r.text[:500]}'}
        data = r.json()
        items = data.get('items', data) if isinstance(data, dict) else data
        return {'projects': items, 'total': data.get('total', len(items))}
