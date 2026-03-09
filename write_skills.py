#!/usr/bin/env python3
"""Write all 20 skill main.py implementations to both data/skills/ and skills/ directories."""

import os

BASE = os.path.dirname(os.path.abspath(__file__))

SKILLS = {}

# ============================================================
# 1. web_search
# ============================================================
SKILLS["web_search"] = '''import httpx
import re

async def execute(query, limit=10, region="wt-wt"):
    """Search the internet via DuckDuckGo HTML."""
    url = "https://html.duckduckgo.com/html/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:109.0) Gecko/20100101 Firefox/115.0"}
    data = {"q": query, "kl": region}
    async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
        resp = await client.post(url, data=data, headers=headers)
        resp.raise_for_status()
    html = resp.text
    results = []
    for m in re.finditer(
        r\'<a rel="nofollow" class="result__a" href="([^"]*)"[^>]*>(.*?)</a>\',
        html, re.DOTALL
    ):
        href, title = m.group(1), re.sub(r"<[^>]+>", "", m.group(2)).strip()
        snippet = ""
        snip = re.search(r\'<a class="result__snippet"[^>]*>(.*?)</a>\', html[m.end():m.end()+2000], re.DOTALL)
        if snip:
            snippet = re.sub(r"<[^>]+>", "", snip.group(1)).strip()
        results.append({"title": title, "url": href, "snippet": snippet})
        if len(results) >= limit:
            break
    return {"results": results, "total": len(results), "query": query}
'''

# ============================================================
# 2. api_call
# ============================================================
SKILLS["api_call"] = '''import httpx

async def execute(url, method="GET", headers=None, body=None, auth_type=None, auth_value=None, timeout=30):
    """Make HTTP API calls with full control over headers, body, and authentication."""
    hdrs = dict(headers or {})
    if auth_type and auth_value:
        if auth_type == "bearer":
            hdrs["Authorization"] = f"Bearer {auth_value}"
        elif auth_type == "api_key":
            hdrs["X-API-Key"] = auth_value
        elif auth_type == "basic":
            import base64
            hdrs["Authorization"] = "Basic " + base64.b64encode(auth_value.encode()).decode()
    kwargs = {"headers": hdrs, "timeout": timeout}
    if body is not None:
        if isinstance(body, (dict, list)):
            kwargs["json"] = body
        else:
            kwargs["content"] = str(body)
    async with httpx.AsyncClient(follow_redirects=True) as client:
        resp = await getattr(client, method.lower())(url, **kwargs)
    try:
        resp_body = resp.json()
    except Exception:
        resp_body = resp.text[:5000]
    return {"status_code": resp.status_code, "headers": dict(resp.headers), "body": resp_body}
'''

# ============================================================
# 3. csv_parse
# ============================================================
SKILLS["csv_parse"] = '''import csv
import io
import statistics

def execute(text=None, file_path=None, operation="parse", columns=None, filter_expr=None, limit=100):
    """Parse, filter, and analyze CSV data."""
    if not text and not file_path:
        return {"error": "Either text or file_path is required"}
    if file_path and not text:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
    reader = csv.DictReader(io.StringIO(text))
    rows = []
    for row in reader:
        if columns:
            row = {k: v for k, v in row.items() if k in columns}
        rows.append(row)
    if operation == "stats":
        stats = {}
        all_cols = rows[0].keys() if rows else []
        for col in all_cols:
            vals = []
            for r in rows:
                try:
                    vals.append(float(r[col]))
                except (ValueError, TypeError):
                    pass
            if vals:
                stats[col] = {
                    "count": len(vals),
                    "mean": round(statistics.mean(vals), 4),
                    "min": min(vals),
                    "max": max(vals),
                    "sum": round(sum(vals), 4),
                }
                if len(vals) > 1:
                    stats[col]["stdev"] = round(statistics.stdev(vals), 4)
        return {"stats": stats, "total_rows": len(rows)}
    return {"rows": rows[:limit], "total_rows": len(rows), "columns": list(rows[0].keys()) if rows else []}
'''

# ============================================================
# 4. math_calculate
# ============================================================
SKILLS["math_calculate"] = '''import math
import statistics as stat_mod

def execute(expression, operation="eval", data=None):
    """Evaluate math expressions safely. Supports arithmetic, trig, log, statistics."""
    if operation == "statistics" and data:
        result = {
            "count": len(data),
            "sum": sum(data),
            "mean": round(stat_mod.mean(data), 6),
            "median": round(stat_mod.median(data), 6),
            "min": min(data),
            "max": max(data),
        }
        if len(data) > 1:
            result["stdev"] = round(stat_mod.stdev(data), 6)
            result["variance"] = round(stat_mod.variance(data), 6)
        return {"result": result}
    allowed_names = {
        "abs": abs, "round": round, "min": min, "max": max, "sum": sum,
        "int": int, "float": float, "pow": pow, "len": len,
        "pi": math.pi, "e": math.e, "tau": math.tau, "inf": math.inf,
        "sqrt": math.sqrt, "cbrt": lambda x: x ** (1/3),
        "sin": math.sin, "cos": math.cos, "tan": math.tan,
        "asin": math.asin, "acos": math.acos, "atan": math.atan, "atan2": math.atan2,
        "log": math.log, "log2": math.log2, "log10": math.log10,
        "exp": math.exp, "ceil": math.ceil, "floor": math.floor,
        "factorial": math.factorial, "gcd": math.gcd,
        "radians": math.radians, "degrees": math.degrees,
        "hypot": math.hypot, "isnan": math.isnan, "isinf": math.isinf,
    }
    try:
        code = compile(expression, "<math>", "eval")
        for name in code.co_names:
            if name not in allowed_names:
                return {"error": f"Function or variable not allowed: {name}"}
        result = eval(code, {"__builtins__": {}}, allowed_names)
        return {"expression": expression, "result": result}
    except Exception as exc:
        return {"error": str(exc), "expression": expression}
'''

# ============================================================
# 5. yaml_parse
# ============================================================
SKILLS["yaml_parse"] = '''import yaml
import json

def execute(text=None, file_path=None, operation="parse"):
    """Parse, validate, and convert YAML data."""
    if not text and not file_path:
        return {"error": "Either text or file_path is required"}
    if file_path and not text:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as e:
        return {"error": f"YAML parse error: {e}", "valid": False}
    if operation == "validate":
        return {"valid": True, "type": type(data).__name__}
    if operation == "to_json":
        return {"json": json.dumps(data, indent=2, ensure_ascii=False, default=str)}
    return {"data": data, "type": type(data).__name__}
'''

# ============================================================
# 6. xml_parse
# ============================================================
SKILLS["xml_parse"] = '''import xml.etree.ElementTree as ET
import json

def _elem_to_dict(elem):
    result = {}
    if elem.attrib:
        result["@attributes"] = dict(elem.attrib)
    if elem.text and elem.text.strip():
        if not list(elem):
            return elem.text.strip()
        result["#text"] = elem.text.strip()
    for child in elem:
        child_data = _elem_to_dict(child)
        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if tag in result:
            if not isinstance(result[tag], list):
                result[tag] = [result[tag]]
            result[tag].append(child_data)
        else:
            result[tag] = child_data
    return result or (elem.text.strip() if elem.text else "")

def execute(text=None, file_path=None, xpath=None, output_format="json"):
    """Parse XML data, optionally query with XPath."""
    if not text and not file_path:
        return {"error": "Either text or file_path is required"}
    if file_path and not text:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
    try:
        root = ET.fromstring(text)
    except ET.ParseError as e:
        return {"error": f"XML parse error: {e}"}
    if xpath:
        elements = root.findall(xpath)
        results = [_elem_to_dict(el) for el in elements]
        return {"results": results, "count": len(results), "xpath": xpath}
    tag = root.tag.split("}")[-1] if "}" in root.tag else root.tag
    return {"root_tag": tag, "data": _elem_to_dict(root)}
'''

# ============================================================
# 7. regex_extract
# ============================================================
SKILLS["regex_extract"] = '''import re

def execute(text, pattern, operation="extract", replacement=None, flags=""):
    """Extract data from text using regex patterns."""
    re_flags = 0
    if "i" in flags:
        re_flags |= re.IGNORECASE
    if "m" in flags:
        re_flags |= re.MULTILINE
    if "s" in flags:
        re_flags |= re.DOTALL
    try:
        compiled = re.compile(pattern, re_flags)
    except re.error as e:
        return {"error": f"Invalid regex: {e}"}
    if operation == "match":
        m = compiled.search(text)
        if not m:
            return {"match": False}
        return {"match": True, "full": m.group(0), "groups": list(m.groups()), "groupdict": m.groupdict(), "span": list(m.span())}
    if operation == "replace":
        if replacement is None:
            return {"error": "replacement is required for replace operation"}
        result = compiled.sub(replacement, text)
        return {"result": result, "replacements": len(compiled.findall(text))}
    if operation == "split":
        parts = compiled.split(text)
        return {"parts": parts, "count": len(parts)}
    # default: extract
    matches = []
    for m in compiled.finditer(text):
        entry = {"match": m.group(0), "span": list(m.span())}
        if m.groups():
            entry["groups"] = list(m.groups())
        if m.groupdict():
            entry["named"] = m.groupdict()
        matches.append(entry)
    return {"matches": matches, "total": len(matches)}
'''

# ============================================================
# 8. rss_read
# ============================================================
SKILLS["rss_read"] = '''import httpx
import xml.etree.ElementTree as ET

async def execute(url, limit=20):
    """Read and parse RSS/Atom feeds."""
    async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
        resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0 (compatible; bot/1.0)"})
        resp.raise_for_status()
    root = ET.fromstring(resp.text)
    entries = []
    # RSS 2.0
    for item in root.iter("item"):
        entry = {}
        for field in ("title", "link", "description", "pubDate", "author", "guid"):
            el = item.find(field)
            if el is not None and el.text:
                entry[field] = el.text.strip()
        if "description" in entry:
            entry["description"] = entry["description"][:500]
        entries.append(entry)
    # Atom
    if not entries:
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        for item in root.findall(".//atom:entry", ns):
            entry = {}
            t = item.find("atom:title", ns)
            if t is not None and t.text:
                entry["title"] = t.text.strip()
            link = item.find("atom:link", ns)
            if link is not None:
                entry["link"] = link.get("href", "")
            s = item.find("atom:summary", ns)
            if s is not None and s.text:
                entry["description"] = s.text.strip()[:500]
            u = item.find("atom:updated", ns)
            if u is not None and u.text:
                entry["pubDate"] = u.text.strip()
            entries.append(entry)
    return {"entries": entries[:limit], "total": len(entries), "feed_url": url}
'''

# ============================================================
# 9. pdf_read
# ============================================================
SKILLS["pdf_read"] = '''import os

async def execute(file_path=None, url=None, pages="all", max_chars=10000):
    """Extract text from PDF files. Tries PyMuPDF (fitz) first, falls back to basic extraction."""
    if not file_path and not url:
        return {"error": "Either file_path or url is required"}
    if url and not file_path:
        import httpx
        async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
            resp = await client.get(url)
            resp.raise_for_status()
        file_path = "/tmp/_skill_pdf_temp.pdf"
        with open(file_path, "wb") as f:
            f.write(resp.content)
    if not os.path.exists(file_path):
        return {"error": f"File not found: {file_path}"}
    text = ""
    page_count = 0
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(file_path)
        page_count = len(doc)
        if pages == "all":
            page_nums = range(page_count)
        elif "-" in str(pages):
            start, end = pages.split("-")
            page_nums = range(int(start) - 1, min(int(end), page_count))
        else:
            page_nums = [int(pages) - 1]
        for i in page_nums:
            if i < page_count:
                text += doc[i].get_text() + "\\n"
        doc.close()
    except ImportError:
        with open(file_path, "rb") as f:
            raw = f.read()
        import re
        chunks = re.findall(rb"\\(([^)]+)\\)", raw)
        text = b" ".join(chunks).decode("latin-1", errors="replace")
        text = re.sub(r"[\\x00-\\x08\\x0b-\\x0c\\x0e-\\x1f]", "", text)
    text = text[:max_chars]
    return {"text": text, "length": len(text), "pages": page_count}
'''

# ============================================================
# 10. project_search_code
# ============================================================
SKILLS["project_search_code"] = '''import os
import re
import fnmatch

def execute(project_slug, query, is_regex=False, file_pattern=None, max_results=50):
    """Search through project source files by text or regex pattern."""
    projects_dir = os.environ.get("PROJECTS_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "projects"))
    project_dir = os.path.join(projects_dir, project_slug)
    if not os.path.isdir(project_dir):
        return {"error": f"Project directory not found: {project_slug}"}
    skip_dirs = {".git", "node_modules", "__pycache__", ".venv", "venv", ".next", "dist", "build", ".idea"}
    if is_regex:
        try:
            pat = re.compile(query, re.IGNORECASE)
        except re.error as e:
            return {"error": f"Invalid regex: {e}"}
    results = []
    for root, dirs, files in os.walk(project_dir):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for fname in files:
            if file_pattern and not fnmatch.fnmatch(fname, file_pattern):
                continue
            fpath = os.path.join(root, fname)
            rel_path = os.path.relpath(fpath, project_dir)
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    for line_num, line in enumerate(f, 1):
                        matched = pat.search(line) if is_regex else (query.lower() in line.lower())
                        if matched:
                            results.append({"file": rel_path, "line": line_num, "text": line.rstrip()[:200]})
                            if len(results) >= max_results:
                                return {"results": results, "total": len(results), "truncated": True}
            except (UnicodeDecodeError, PermissionError, IsADirectoryError):
                continue
    return {"results": results, "total": len(results), "truncated": False}
'''

# ============================================================
# 11. git_operations
# ============================================================
SKILLS["git_operations"] = '''import asyncio
import os

async def execute(operation, project_slug=None, repo_url=None, branch=None, message=None, files=None):
    """Perform git operations: clone, status, diff, commit, push, pull, log, branch, checkout."""
    projects_dir = os.environ.get("PROJECTS_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "projects"))
    cwd = os.path.join(projects_dir, project_slug) if project_slug else projects_dir
    async def run(cmd):
        proc = await asyncio.create_subprocess_shell(
            cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=cwd
        )
        out, err = await proc.communicate()
        return {"stdout": out.decode()[:5000], "stderr": err.decode()[:2000], "returncode": proc.returncode}
    if operation == "clone":
        if not repo_url:
            return {"error": "repo_url is required for clone"}
        target = os.path.join(projects_dir, project_slug) if project_slug else projects_dir
        return await run(f"git clone {repo_url} {target}")
    elif operation == "status":
        return await run("git status --porcelain")
    elif operation == "diff":
        return await run("git diff")
    elif operation == "commit":
        msg = message or "Auto commit"
        if files:
            await run("git add " + " ".join(files))
        else:
            await run("git add -A")
        return await run(f'git commit -m "{msg}"')
    elif operation == "push":
        cmd = f"git push origin {branch}" if branch else "git push"
        return await run(cmd)
    elif operation == "pull":
        cmd = f"git pull origin {branch}" if branch else "git pull"
        return await run(cmd)
    elif operation == "log":
        return await run("git log --oneline -20")
    elif operation == "branch":
        if branch:
            return await run(f"git checkout -b {branch}")
        return await run("git branch -a")
    elif operation == "checkout":
        if not branch:
            return {"error": "branch is required for checkout"}
        return await run(f"git checkout {branch}")
    return {"error": f"Unknown git operation: {operation}"}
'''

# ============================================================
# 12. docker_manage
# ============================================================
SKILLS["docker_manage"] = '''import asyncio

async def execute(operation, container=None, tail=50):
    """Manage Docker containers: list, start, stop, restart, logs, status, images."""
    async def run(cmd):
        proc = await asyncio.create_subprocess_shell(
            cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        out, err = await proc.communicate()
        return {"stdout": out.decode()[:5000], "stderr": err.decode()[:2000], "returncode": proc.returncode}
    if operation == "list":
        return await run("docker ps --format 'table {{.Names}}\\t{{.Status}}\\t{{.Ports}}\\t{{.Image}}'")
    elif operation == "start":
        if not container:
            return {"error": "container name required"}
        return await run(f"docker start {container}")
    elif operation == "stop":
        if not container:
            return {"error": "container name required"}
        return await run(f"docker stop {container}")
    elif operation == "restart":
        if not container:
            return {"error": "container name required"}
        return await run(f"docker restart {container}")
    elif operation == "logs":
        if not container:
            return {"error": "container name required"}
        return await run(f"docker logs --tail {tail} {container}")
    elif operation == "status":
        if container:
            return await run(f"docker inspect --format '{{{{.State.Status}}}}' {container}")
        return await run("docker ps -a --format 'table {{.Names}}\\t{{.Status}}'")
    elif operation == "images":
        return await run("docker images --format 'table {{.Repository}}\\t{{.Tag}}\\t{{.Size}}'")
    return {"error": f"Unknown docker operation: {operation}"}
'''

# ============================================================
# 13. email_send
# ============================================================
SKILLS["email_send"] = '''import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

def execute(to, subject, body, html=False, reply_to=None):
    """Send email via SMTP. Requires SMTP env vars or system settings."""
    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_PASSWORD", "")
    if not smtp_user or not smtp_pass:
        return {"error": "SMTP credentials not configured. Set SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD."}
    msg = MIMEMultipart("alternative")
    msg["From"] = smtp_user
    msg["To"] = to
    msg["Subject"] = subject
    if reply_to:
        msg["Reply-To"] = reply_to
    content_type = "html" if html else "plain"
    msg.attach(MIMEText(body, content_type, "utf-8"))
    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        return {"sent": True, "to": to, "subject": subject}
    except Exception as e:
        return {"error": f"Failed to send email: {e}"}
'''

# ============================================================
# 14. telegram_send — needs running Telethon client, pipeline handler is primary
# ============================================================
SKILLS["telegram_send"] = '''# Telegram message sending — requires running Telethon client from messenger config.
# Primary execution path is via the pipeline handler (_sys_telegram_send).
# This standalone fallback will not work without active messenger sessions.

async def execute(messenger_id, chat_id, text, parse_mode="markdown"):
    """Send a Telegram message. Requires active messenger session in pipeline context."""
    return {
        "error": "telegram_send requires an active Telethon session. "
                 "This skill must be executed through the pipeline handler, "
                 "not standalone. Ensure a Telegram messenger is configured and running."
    }
'''

# ============================================================
# 15. notification_send — needs messenger access, pipeline handler is primary
# ============================================================
SKILLS["notification_send"] = '''# Notification sending — routes through configured messenger.
# Primary execution path is via the pipeline handler (_sys_notification_send).

async def execute(title, message, priority="normal"):
    """Send a notification to the owner. Requires pipeline context for messenger access."""
    return {
        "error": "notification_send requires messenger context from the pipeline. "
                 "This skill must be executed through the pipeline handler."
    }
'''

# ============================================================
# 16. image_analyze — needs LLM with vision
# ============================================================
SKILLS["image_analyze"] = '''# Image analysis using vision-capable LLM.
# Primary execution path is via the pipeline handler (_sys_image_analyze).

async def execute(image_url, question="Describe this image in detail"):
    """Analyze an image using vision LLM. Requires pipeline context for LLM access."""
    return {
        "error": "image_analyze requires a vision-capable LLM accessed through the pipeline. "
                 "This skill must be executed through the pipeline handler."
    }
'''

# ============================================================
# 17. image_generate — needs OpenAI API key
# ============================================================
SKILLS["image_generate"] = '''import httpx
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
'''

# ============================================================
# 18. translate — needs LLM, pipeline primary, but can fallback to free API
# ============================================================
SKILLS["translate"] = '''import httpx

async def execute(text, to_language, from_language=None):
    """Translate text between languages. Tries MyMemory free API as standalone fallback."""
    src = from_language or "autodetect"
    lang_map = {
        "english": "en", "russian": "ru", "spanish": "es", "french": "fr",
        "german": "de", "italian": "it", "portuguese": "pt", "chinese": "zh",
        "japanese": "ja", "korean": "ko", "arabic": "ar", "hindi": "hi",
        "dutch": "nl", "polish": "pl", "turkish": "tr", "swedish": "sv",
        "czech": "cs", "ukrainian": "uk",
    }
    src_code = lang_map.get(src.lower(), src.lower()[:2]) if src != "autodetect" else "autodetect"
    tgt_code = lang_map.get(to_language.lower(), to_language.lower()[:2])
    langpair = f"{src_code}|{tgt_code}"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                "https://api.mymemory.translated.net/get",
                params={"q": text[:500], "langpair": langpair},
            )
            data = resp.json()
        translated = data.get("responseData", {}).get("translatedText", "")
        if translated:
            return {"translated": translated, "from": src, "to": to_language, "source": "mymemory"}
        return {"error": f"Translation failed: {data.get('responseStatus', 'unknown')}"}
    except Exception as e:
        return {"error": f"Translation error: {e}. For better results, use through pipeline with LLM."}
'''

# ============================================================
# 19. schedule_reminder — needs MongoDB, pipeline handler is primary
# ============================================================
SKILLS["schedule_reminder"] = '''# Reminder scheduling — creates a task in MongoDB.
# Primary execution path is via the pipeline handler (_sys_schedule_reminder).

async def execute(title, message, trigger_at, recurring=False):
    """Schedule a reminder. Requires pipeline context for database access."""
    return {
        "error": "schedule_reminder requires database access through the pipeline. "
                 "This skill must be executed through the pipeline handler."
    }
'''

# ============================================================
# 20. code_review — needs LLM, pipeline handler is primary
# ============================================================
SKILLS["code_review"] = '''import os

def execute(code=None, file_path=None, language=None, focus="all"):
    """Review code for bugs, security, style, performance. Returns basic static analysis standalone."""
    if not code and not file_path:
        return {"error": "Either code or file_path is required"}
    if file_path and not code:
        if not os.path.exists(file_path):
            return {"error": f"File not found: {file_path}"}
        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()
    if not language:
        if file_path:
            ext = os.path.splitext(file_path)[1]
            lang_map = {".py": "python", ".js": "javascript", ".ts": "typescript", ".go": "go", ".rs": "rust", ".java": "java", ".rb": "ruby", ".php": "php"}
            language = lang_map.get(ext, "unknown")
        else:
            language = "unknown"
    issues = []
    lines = code.split("\\n")
    for i, line in enumerate(lines, 1):
        stripped = line.rstrip()
        if len(stripped) > 120:
            issues.append({"line": i, "type": "style", "message": f"Line too long ({len(stripped)} chars)"})
        if "TODO" in line or "FIXME" in line or "HACK" in line:
            issues.append({"line": i, "type": "info", "message": f"Found marker: {stripped.strip()[:80]}"})
        if language == "python":
            if "eval(" in line and "safe" not in line.lower():
                issues.append({"line": i, "type": "security", "message": "Potential unsafe eval() usage"})
            if "exec(" in line:
                issues.append({"line": i, "type": "security", "message": "Potential unsafe exec() usage"})
            if "import *" in line:
                issues.append({"line": i, "type": "style", "message": "Wildcard import"})
            if "except:" in line and "except Exception" not in line:
                issues.append({"line": i, "type": "bugs", "message": "Bare except clause"})
            if "password" in line.lower() and "=" in line and ("'" in line or '"' in line):
                issues.append({"line": i, "type": "security", "message": "Possible hardcoded password"})
        if language in ("javascript", "typescript"):
            if "eval(" in line:
                issues.append({"line": i, "type": "security", "message": "eval() usage"})
            if "var " in line:
                issues.append({"line": i, "type": "style", "message": "Use let/const instead of var"})
            if "console.log" in line:
                issues.append({"line": i, "type": "info", "message": "console.log found"})
    if focus != "all":
        issues = [iss for iss in issues if iss["type"] == focus]
    return {
        "language": language, "total_lines": len(lines), "issues": issues[:50],
        "issue_count": len(issues),
        "note": "Basic static analysis only. For deeper LLM-powered review, execute through the pipeline handler."
    }
'''


def write_skill(name, code):
    for base_dir in ["data/skills", "skills"]:
        path = os.path.join(BASE, base_dir, name, "main.py")
        if os.path.exists(os.path.dirname(path)):
            with open(path, "w", encoding="utf-8") as f:
                f.write(code.lstrip("\n"))
            print(f"  OK: {base_dir}/{name}/main.py")
        else:
            print(f"  SKIP: {base_dir}/{name}/ (dir not found)")


if __name__ == "__main__":
    for name, code in SKILLS.items():
        print(f"Writing: {name}")
        write_skill(name, code)
    print(f"\nDone! Wrote {len(SKILLS)} skills.")
