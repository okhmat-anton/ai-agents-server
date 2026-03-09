#!/usr/bin/env python3
"""
Update skill_service.py code fields and MongoDB skill documents with real implementations.
Reads main.py from data/skills/{name}/main.py and:
1. Updates the `"code": "..."` field in SYSTEM_SKILLS entries in skill_service.py
2. Updates the `code` field in MongoDB skills collection
"""

import os
import re
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
SKILL_SERVICE = os.path.join(BASE, "backend", "app", "services", "skill_service.py")

# Map of skill_name -> old code comment in skill_service.py
SKILL_CODE_COMMENTS = {
    "web_search": "# Web search — executed by pipeline handler",
    "telegram_send": "# Telegram send — executed by pipeline handler",
    "notification_send": "# Notification — executed by pipeline handler",
    "image_analyze": "# Image analysis — executed by pipeline handler",
    "git_operations": "# Git operations — executed by pipeline handler",
    "project_search_code": "# Project code search — executed by pipeline handler",
    "image_generate": "# Image generation — executed by pipeline handler",
    "translate": "# Translation — executed by pipeline handler",
    "csv_parse": "# CSV parsing — executed by pipeline handler",
    "pdf_read": "# PDF reading — executed by pipeline handler",
    "email_send": "# Email sending — executed by pipeline handler",
    "schedule_reminder": "# Reminder scheduling — executed by pipeline handler",
    "yaml_parse": "# YAML parsing — executed by pipeline handler",
    "xml_parse": "# XML parsing — executed by pipeline handler",
    "regex_extract": "# Regex extraction — executed by pipeline handler",
    "api_call": "# API call — executed by pipeline handler",
    "math_calculate": "# Math calculations — executed by pipeline handler",
    "code_review": "# Code review — executed by pipeline handler",
    "docker_manage": "# Docker management — executed by pipeline handler",
    "rss_read": "# RSS feed reader — executed by pipeline handler",
}


def update_skill_service():
    """Replace code comments with actual code in skill_service.py."""
    with open(SKILL_SERVICE, "r", encoding="utf-8") as f:
        content = f.read()

    updated = 0
    for skill_name, old_comment in SKILL_CODE_COMMENTS.items():
        main_py = os.path.join(BASE, "data", "skills", skill_name, "main.py")
        if not os.path.exists(main_py):
            print(f"  SKIP {skill_name}: main.py not found")
            continue

        with open(main_py, "r", encoding="utf-8") as f:
            code = f.read().strip()

        # Escape for Python string literal (inside double quotes)
        escaped = code.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")

        old_pattern = f'"code": "{old_comment}"'
        new_value = f'"code": "{escaped}"'

        if old_pattern in content:
            content = content.replace(old_pattern, new_value, 1)
            updated += 1
            print(f"  OK: {skill_name}")
        else:
            print(f"  NOT FOUND: {skill_name} (pattern: {old_pattern[:60]}...)")

    with open(SKILL_SERVICE, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"\nUpdated {updated}/{len(SKILL_CODE_COMMENTS)} code fields in skill_service.py")
    return updated


async def update_mongodb():
    """Update code fields in MongoDB for existing skills."""
    try:
        sys.path.insert(0, os.path.join(BASE, "backend"))
        os.environ.setdefault("PYTHONPATH", os.path.join(BASE, "backend"))

        from motor.motor_asyncio import AsyncIOMotorClient

        # Read connection settings
        mongo_url = os.environ.get("MONGODB_URL", "mongodb://agents:mongo_secret_2026@localhost:4717/ai_agents")
        client = AsyncIOMotorClient(mongo_url)
        db = client.get_default_database()

        updated = 0
        for skill_name in SKILL_CODE_COMMENTS:
            main_py = os.path.join(BASE, "data", "skills", skill_name, "main.py")
            if not os.path.exists(main_py):
                continue
            with open(main_py, "r", encoding="utf-8") as f:
                code = f.read().strip()

            result = await db.skills.update_one(
                {"name": skill_name},
                {"$set": {"code": code}}
            )
            if result.modified_count > 0:
                updated += 1
                print(f"  MongoDB OK: {skill_name}")
            elif result.matched_count > 0:
                print(f"  MongoDB UNCHANGED: {skill_name} (already up to date)")
            else:
                print(f"  MongoDB NOT FOUND: {skill_name}")

        client.close()
        print(f"\nUpdated {updated} skills in MongoDB")
        return updated
    except Exception as e:
        print(f"\nMongoDB update failed: {e}")
        return 0


if __name__ == "__main__":
    print("=" * 60)
    print("Step 1: Updating skill_service.py code fields...")
    print("=" * 60)
    update_skill_service()

    print("\n" + "=" * 60)
    print("Step 2: Updating MongoDB skill documents...")
    print("=" * 60)
    import asyncio
    asyncio.run(update_mongodb())

    print("\nDone!")
