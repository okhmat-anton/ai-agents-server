#!/usr/bin/env python3
"""Debug: check chat session and messages in MongoDB."""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def check():
    client = AsyncIOMotorClient('mongodb://agents:mongo_secret_2026@localhost:4717')
    db = client['ai_agents']

    session_id = 'a03b3fa2-2897-440e-8c2a-4261e897940d'

    # Check session
    session = await db.chat_sessions.find_one({'_id': session_id})
    if session:
        print(f"Session found: _id={session['_id']}, title={session.get('title')}")
    else:
        print("Session NOT FOUND")

    # Check messages for this session
    msgs = await db.chat_messages.find({'session_id': session_id}).to_list(100)
    print(f"Messages with session_id={session_id}: {len(msgs)}")

    for m in msgs[:3]:
        print(f"  msg _id={m.get('_id')}, role={m.get('role')}, content={m.get('content','')[:80]}")

    # Check total messages in collection
    total = await db.chat_messages.count_documents({})
    print(f"Total messages in collection: {total}")

    # Sample a message to see session_id format
    sample = await db.chat_messages.find_one()
    if sample:
        print(f"Sample msg: session_id={sample.get('session_id')} (type={type(sample.get('session_id')).__name__})")
        print(f"Sample msg: _id={sample.get('_id')}, role={sample.get('role')}")

    # All distinct session_ids in messages
    sids = await db.chat_messages.distinct('session_id')
    print(f"Distinct session_ids in messages ({len(sids)}): {sids[:10]}")

    # All sessions
    sessions = await db.chat_sessions.find({}).to_list(50)
    print(f"Total sessions: {len(sessions)}")
    for s in sessions[:5]:
        print(f"  session _id={s['_id']}, title={s.get('title')}, chat_type={s.get('chat_type')}")

    client.close()

asyncio.run(check())
