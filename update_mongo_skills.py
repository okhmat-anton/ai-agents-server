#!/usr/bin/env python3
"""Update MongoDB skill code fields with real implementations."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))

from motor.motor_asyncio import AsyncIOMotorClient

BASE = os.path.dirname(os.path.abspath(__file__))

SKILLS = [
    "web_search", "telegram_send", "notification_send", "image_analyze",
    "git_operations", "project_search_code", "image_generate", "translate",
    "csv_parse", "pdf_read", "email_send", "schedule_reminder",
    "yaml_parse", "xml_parse", "regex_extract", "api_call",
    "math_calculate", "code_review", "docker_manage", "rss_read",
]


async def main():
    client = AsyncIOMotorClient("mongodb://agents:mongo_secret_2026@localhost:4717/ai_agents?authSource=admin")
    db = client.get_default_database()
    updated = 0
    for name in SKILLS:
        path = os.path.join(BASE, "data", "skills", name, "main.py")
        if not os.path.exists(path):
            print(f"SKIP: {name}")
            continue
        with open(path, "r", encoding="utf-8") as f:
            code = f.read().strip()
        r = await db.skills.update_one({"name": name}, {"$set": {"code": code}})
        if r.modified_count > 0:
            updated += 1
            print(f"OK: {name}")
        elif r.matched_count > 0:
            print(f"SAME: {name}")
        else:
            print(f"NOT_FOUND: {name}")
    client.close()
    print(f"\nUpdated {updated} skills in MongoDB")


if __name__ == "__main__":
    asyncio.run(main())
