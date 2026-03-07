import os
import json
import urllib.request

# Load .env.agent
with open('.env.agent') as f:
    for line in f:
        if '=' in line and not line.strip().startswith('#'):
            key, value = line.strip().split('=', 1)
            os.environ[key] = value.strip('"\'')

api_url = os.environ['AGENT_API_URL']
api_key = os.environ['AGENT_API_KEY']

with open('ais34_completion.md') as f:
    comment_content = f.read()

data = json.dumps({'content': comment_content, 'is_internal': False}).encode('utf-8')
req = urllib.request.Request(
    f'{api_url}/issues/69abcc93fde3be2f19e9e99c/comments',
    data=data,
    headers={
        'X-Agent-Key': api_key,
        'Content-Type': 'application/json'
    },
    method='POST'
)

try:
    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode('utf-8'))
        print(f'✅ Completion comment posted: {result["id"]}')
        print(f'   Created at: {result["created_at"]}')
except Exception as e:
    print(f'❌ Error: {e}')
