from sqlalchemy.ext.asyncio import AsyncSession
from app.models.skill import Skill
from sqlalchemy import select
from app.api.skill_files import init_skill_directory


SYSTEM_SKILLS = [
    {
        "name": "web_fetch",
        "display_name": "Web Fetch",
        "description": "HTTP GET/POST requests to URL",
        "category": "web",
        "code": "import httpx\nasync def execute(url, method='GET', **kwargs):\n    async with httpx.AsyncClient() as c:\n        r = await getattr(c, method.lower())(url, **kwargs)\n        return {'status': r.status_code, 'text': r.text[:5000]}",
        "input_schema": {"type": "object", "properties": {"url": {"type": "string"}, "method": {"type": "string", "default": "GET"}}},
    },
    {
        "name": "web_scrape",
        "display_name": "Web Scrape",
        "description": "Parse HTML pages (BeautifulSoup)",
        "category": "web",
        "code": "# HTML scraping skill",
        "input_schema": {"type": "object", "properties": {"url": {"type": "string"}, "selector": {"type": "string"}}},
    },
    {
        "name": "file_read",
        "display_name": "File Read",
        "description": "Read files from filesystem",
        "category": "files",
        "code": "async def execute(path):\n    with open(path) as f:\n        return {'content': f.read()}",
        "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}},
    },
    {
        "name": "file_write",
        "display_name": "File Write",
        "description": "Write files to filesystem",
        "category": "files",
        "code": "async def execute(path, content):\n    with open(path, 'w') as f:\n        f.write(content)\n    return {'written': len(content)}",
        "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}},
    },
    {
        "name": "shell_exec",
        "display_name": "Shell Execute",
        "description": "Execute shell commands (sandbox)",
        "category": "code",
        "code": "import asyncio\nasync def execute(command):\n    proc = await asyncio.create_subprocess_shell(command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)\n    stdout, stderr = await proc.communicate()\n    return {'stdout': stdout.decode()[:5000], 'stderr': stderr.decode()[:2000], 'returncode': proc.returncode}",
        "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}},
    },
    {
        "name": "code_execute",
        "display_name": "Code Execute",
        "description": "Execute Python code (sandbox)",
        "category": "code",
        "code": "# Python code execution in sandbox",
        "input_schema": {"type": "object", "properties": {"code": {"type": "string"}}},
    },
    {
        "name": "json_parse",
        "display_name": "JSON Parse",
        "description": "Parse and transform JSON",
        "category": "data",
        "code": "import json\ndef execute(text):\n    return json.loads(text)",
        "input_schema": {"type": "object", "properties": {"text": {"type": "string"}}},
    },
    {
        "name": "text_summarize",
        "display_name": "Text Summarize",
        "description": "Summarize text using LLM",
        "category": "general",
        "code": "# Uses LLM to summarize text",
        "input_schema": {"type": "object", "properties": {"text": {"type": "string"}, "max_length": {"type": "integer", "default": 200}}},
    },
    {
        "name": "memory_store",
        "display_name": "Memory Store",
        "description": "Save information to long-term memory",
        "category": "general",
        "code": "# Stores memory entry via MemoryService",
        "input_schema": {"type": "object", "properties": {"title": {"type": "string"}, "content": {"type": "string"}, "type": {"type": "string"}, "importance": {"type": "number"}, "tags": {"type": "array"}}},
    },
    {
        "name": "memory_search",
        "display_name": "Memory Search",
        "description": "Semantic search through agent memory",
        "category": "general",
        "code": "# Searches memory via MemoryService",
        "input_schema": {"type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "integer", "default": 5}}},
    },
    {
        "name": "memory_deep_process",
        "display_name": "Memory Deep Process",
        "description": "Analyze all memory records, establish typed links between them, build knowledge graph (see Memory Links)",
        "category": "general",
        "code": "# Deep memory processing: analyzes all records and creates links",
        "input_schema": {"type": "object", "properties": {"depth": {"type": "integer", "default": 2}}},
    },
]


async def create_system_skills(db: AsyncSession):
    """Create system skills if not exists."""
    for skill_data in SYSTEM_SKILLS:
        result = await db.execute(select(Skill).where(Skill.name == skill_data["name"]))
        if result.scalar_one_or_none():
            continue

        skill = Skill(
            name=skill_data["name"],
            display_name=skill_data["display_name"],
            description=skill_data["description"],
            category=skill_data["category"],
            code=skill_data["code"],
            input_schema=skill_data.get("input_schema", {}),
            is_system=True,
            is_shared=True,
        )
        db.add(skill)
        await db.flush()
        await db.refresh(skill)

        # Create filesystem directory + manifest
        init_skill_directory(skill)

    await db.commit()
