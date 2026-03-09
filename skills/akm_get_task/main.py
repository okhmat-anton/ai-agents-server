import httpx
import os
async def execute(project_id, task_id):
    api_key = os.environ.get('AKM_ADVISOR_API_KEY', '')
    base_url = os.environ.get('AKM_ADVISOR_URL', 'https://app.akm-advisor.com')
    if not api_key:
        return {'error': 'AKM Advisor API key not configured.'}
    headers = {'Authorization': f'Bearer {api_key}'}
    async with httpx.AsyncClient(timeout=20, verify=False) as client:
        r = await client.get(f'{base_url}/api/v1/agent/{project_id}/issues/{task_id}', headers=headers)
        if r.status_code != 200:
            return {'error': f'API error {r.status_code}: {r.text[:500]}'}
        return r.json()
