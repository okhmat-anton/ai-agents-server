import httpx
import os
async def execute(project_id, status=None, include_done=False):
    api_key = os.environ.get('AKM_ADVISOR_API_KEY', '')
    base_url = os.environ.get('AKM_ADVISOR_URL', 'https://app.akm-advisor.com')
    if not api_key:
        return {'error': 'AKM Advisor API key not configured.'}
    headers = {'Authorization': f'Bearer {api_key}'}
    params = {'limit': 200, 'include_done': str(include_done).lower()}
    if status:
        params['status'] = status
    async with httpx.AsyncClient(timeout=20, verify=False) as client:
        r = await client.get(f'{base_url}/api/v1/agent/{project_id}/issues', headers=headers, params=params)
        if r.status_code != 200:
            return {'error': f'API error {r.status_code}: {r.text[:500]}'}
        data = r.json()
        items = data.get('items', data) if isinstance(data, dict) else data
        return {'tasks': items, 'total': data.get('total', len(items))}
