import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def check():
    client = AsyncIOMotorClient('mongodb://agents:mongo_secret_2026@localhost:4717/ai_agents?authSource=admin')
    db = client['ai_agents']
    
    # Get the latest session
    sessions = await db['chat_sessions'].find().sort('updated_at', -1).limit(3).to_list(3)
    for s in sessions:
        print(f'Session: {s.get("title", "?")} | type={s.get("chat_type")} | models={s.get("model_ids")} | agent={s.get("agent_id")}')
    
    if sessions:
        sid = str(sessions[0].get('id') or sessions[0].get('_id'))
        print(f'\nChecking session: {sid}')
        msgs = await db['chat_messages'].find({'session_id': sid}).sort('created_at', -1).limit(2).to_list(2)
        for m in msgs:
            content = m.get('content', '')
            print(f'\n  [{m["role"]}] len={len(content)} tokens={m.get("total_tokens",0)} completion_tokens={m.get("completion_tokens",0)}')
            print(f'  Last 300 chars: ...{content[-300:]}')
            # Check if it ends mid-sentence
            ends_with = content.strip()[-20:] if content.strip() else ''
            last_char = content.strip()[-1] if content.strip() else ''
            print(f'  Ends with: "{ends_with}"')
            print(f'  Last char: "{last_char}" (likely truncated: {last_char not in ".!?:)>]"})')

asyncio.run(check())
