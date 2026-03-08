"""
Audio service: TTS (Text-to-Speech) and STT (Speech-to-Text) via kie.ai.

kie.ai API is ASYNC — polling loop:
  1. POST https://api.kie.ai/api/v1/jobs/createTask → {taskId}
  2. GET  https://api.kie.ai/api/v1/jobs/recordInfo?taskId={taskId} in a loop until done
  3. TTS: Download audio from resultJson.resultUrls[0]
  4. STT: Extract text from resultJson.resultObject.text

STT requires audio_url (public URL). Audio is uploaded to tmpfiles.org first.

Settings:
  - kieai_api_key:  API key for kie.ai
  - tts_timeout:    Max seconds to wait for task to complete (default 120)
"""
import json
import os
import re
import uuid
import time
import asyncio
import httpx
from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.mongodb.services import SystemSettingService
from app.services.log_service import syslog


AUDIO_DIR = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))).resolve() / "data" / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

KIEAI_API_BASE = "https://api.kie.ai/api/v1/jobs"
KIEAI_CREATE_TASK = f"{KIEAI_API_BASE}/createTask"
KIEAI_RECORD_INFO = f"{KIEAI_API_BASE}/recordInfo"  # + ?taskId=...

KIEAI_TTS_MODEL = "elevenlabs/text-to-speech-turbo-2-5"
KIEAI_STT_MODEL = "elevenlabs/speech-to-text"

KIEAI_MAX_WAIT_DEFAULT = 120  # default max seconds to poll
KIEAI_POLL_INTERVAL = 2  # seconds between poll requests


# ── Helpers ──────────────────────────────────────────────────────────

async def _get_setting(db: AsyncIOMotorDatabase, key: str) -> str | None:
    svc = SystemSettingService(db)
    s = await svc.get_by_key(key)
    return s.value if s else None


def _auth_headers(api_key: str) -> dict:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def _parse_kieai_result_json(raw: str | dict) -> dict:
    """Parse kie.ai resultJson which may have unquoted keys like {resultObject: {...}}.
    
    The kie.ai API sometimes returns non-standard JSON in resultJson field:
      {resultObject: {"language_code": "eng", "text": "..."}}
    instead of:
      {"resultObject": {"language_code": "eng", "text": "..."}}
    """
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str) or not raw.strip():
        return {}

    # Try standard JSON first
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        pass

    # Fix unquoted top-level keys: {key: -> {"key":
    # This handles {resultObject: ...} and {resultUrls: ...}
    fixed = re.sub(r'\{(\s*)(\w+)\s*:', r'{\1"\2":', raw)
    try:
        return json.loads(fixed)
    except (json.JSONDecodeError, TypeError):
        pass

    # Last resort: try to extract resultObject content directly via regex
    # Match {resultObject: { ... }}  — find the inner JSON object
    m = re.search(r'resultObject\s*:\s*(\{.*\})\s*\}?\s*$', raw, re.DOTALL)
    if m:
        try:
            inner = json.loads(m.group(1))
            return {"resultObject": inner}
        except (json.JSONDecodeError, TypeError):
            pass

    # Try resultUrls for TTS format
    m = re.search(r'resultUrls\s*:\s*(\[.*?\])', raw, re.DOTALL)
    if m:
        try:
            urls = json.loads(m.group(1))
            return {"resultUrls": urls}
        except (json.JSONDecodeError, TypeError):
            pass

    raise ValueError(f"Cannot parse kie.ai resultJson: {raw[:500]}")


MIME_MAP = {
    "ogg": "audio/ogg",
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
    "webm": "audio/webm",
    "m4a": "audio/mp4",
    "flac": "audio/flac",
}

# Formats that need conversion to MP3 before sending to kie.ai STT
# (kie.ai returns 500 errors for OGG OPUS and some other formats)
FORMATS_NEED_CONVERSION = {"ogg", "webm", "flac", "m4a"}


async def _convert_audio_to_mp3(audio_data: bytes, source_ext: str) -> tuple[bytes, str]:
    """Convert audio to MP3 using ffmpeg. Returns (mp3_data, 'mp3')."""
    import subprocess
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=f".{source_ext}", delete=False) as src_f:
        src_f.write(audio_data)
        src_path = src_f.name

    dst_path = src_path.rsplit(".", 1)[0] + ".mp3"

    try:
        proc = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: subprocess.run(
                ["ffmpeg", "-i", src_path, "-acodec", "libmp3lame", "-q:a", "4", "-y", dst_path],
                capture_output=True, timeout=30,
            ),
        )

        if proc.returncode != 0:
            stderr = proc.stderr.decode(errors="replace")[:500]
            await syslog("warning", f"ffmpeg conversion failed: {stderr}", source="audio")
            # Return original if conversion fails
            return audio_data, source_ext

        mp3_data = Path(dst_path).read_bytes()
        await syslog("debug", f"Audio converted: {source_ext} ({len(audio_data)} bytes) -> mp3 ({len(mp3_data)} bytes)", source="audio")
        return mp3_data, "mp3"
    finally:
        for p in (src_path, dst_path):
            try:
                os.unlink(p)
            except OSError:
                pass


async def _upload_temp_audio(client: httpx.AsyncClient, audio_data: bytes, ext: str = "ogg") -> str:
    """Upload audio to tmpfiles.org (temp hosting) to get a public URL for kie.ai STT."""
    content_type = MIME_MAP.get(ext, "audio/ogg")
    filename = f"audio_{uuid.uuid4().hex[:8]}.{ext}"

    await syslog("debug", f"STT: uploading {len(audio_data)} bytes to tmpfiles.org as {filename}", source="audio")

    resp = await client.post(
        "https://tmpfiles.org/api/v1/upload",
        files={"file": (filename, audio_data, content_type)},
        timeout=60,
    )

    if resp.status_code != 200:
        raise ValueError(f"tmpfiles.org upload failed: HTTP {resp.status_code}: {resp.text[:500]}")

    data = resp.json()
    if data.get("status") != "success":
        raise ValueError(f"tmpfiles.org upload failed: {data}")

    url = (data.get("data") or {}).get("url", "")
    if not url:
        raise ValueError(f"tmpfiles.org returned no URL: {data}")

    # Convert view URL to direct download URL by inserting /dl/ after domain
    # http://tmpfiles.org/12345/file.ogg -> https://tmpfiles.org/dl/12345/file.ogg
    direct_url = url.replace("tmpfiles.org/", "tmpfiles.org/dl/", 1)
    if direct_url.startswith("http://"):
        direct_url = direct_url.replace("http://", "https://", 1)

    await syslog("info", f"STT: audio uploaded to {direct_url}", source="audio")
    return direct_url


# ── kie.ai task creation ─────────────────────────────────────────────

KIEAI_CREATE_RETRIES = 3
KIEAI_CREATE_RETRY_DELAY = 3  # seconds between retries


async def _create_task(
    client: httpx.AsyncClient,
    api_key: str,
    model: str,
    input_data: dict,
) -> str:
    """Submit a task to kie.ai -> returns taskId. Retries on 500 errors."""
    payload = {
        "model": model,
        "input": input_data,
    }

    last_error = None
    for attempt in range(1, KIEAI_CREATE_RETRIES + 1):
        await syslog("debug", f"KIEAI createTask attempt {attempt}/{KIEAI_CREATE_RETRIES}: model={model}", source="audio")

        try:
            resp = await client.post(KIEAI_CREATE_TASK, headers=_auth_headers(api_key), json=payload)
            await syslog("debug", f"KIEAI createTask response: status={resp.status_code}, body={resp.text[:500]}", source="audio")
        except httpx.RequestError as e:
            last_error = f"Request error: {e}"
            await syslog("warning", f"KIEAI createTask attempt {attempt} request error: {e}", source="audio")
            if attempt < KIEAI_CREATE_RETRIES:
                await asyncio.sleep(KIEAI_CREATE_RETRY_DELAY)
                continue
            raise ValueError(f"kie.ai createTask failed after {KIEAI_CREATE_RETRIES} attempts: {last_error}")

        if resp.status_code >= 500:
            last_error = f"HTTP {resp.status_code}: {resp.text[:500]}"
            await syslog("warning", f"KIEAI createTask attempt {attempt}: server error {resp.status_code}, retrying...", source="audio")
            if attempt < KIEAI_CREATE_RETRIES:
                await asyncio.sleep(KIEAI_CREATE_RETRY_DELAY)
                continue
            raise ValueError(f"kie.ai createTask failed after {KIEAI_CREATE_RETRIES} attempts: {last_error}")

        if resp.status_code != 200:
            error_text = resp.text[:1000]
            raise ValueError(f"kie.ai createTask error: HTTP {resp.status_code}: {error_text}")

        body = resp.json()
        code = body.get("code")
        if code and code >= 500:
            last_error = f"API code {code}: {body.get('msg', 'Unknown error')}"
            await syslog("warning", f"KIEAI createTask attempt {attempt}: API error ({code}), retrying...", source="audio")
            if attempt < KIEAI_CREATE_RETRIES:
                await asyncio.sleep(KIEAI_CREATE_RETRY_DELAY)
                continue
            raise ValueError(f"kie.ai createTask failed after {KIEAI_CREATE_RETRIES} attempts: {last_error}")

        if code and code != 200:
            msg = body.get("msg", "Unknown error")
            raise ValueError(f"kie.ai error ({code}): {msg}")

        break  # Success

    task_id = (body.get("data") or {}).get("taskId")
    if not task_id:
        raise ValueError(f"kie.ai createTask returned no taskId: {body}")

    await syslog("info", f"KIEAI task created: {task_id}", source="audio")
    return task_id


# ── kie.ai task polling ──────────────────────────────────────────────

async def _poll_task(
    client: httpx.AsyncClient,
    api_key: str,
    task_id: str,
    max_wait: int,
) -> dict:
    """Poll recordInfo?taskId= until task completes or timeout."""
    url = f"{KIEAI_RECORD_INFO}?taskId={task_id}"
    start = time.time()
    attempt = 0

    while True:
        elapsed = time.time() - start
        if elapsed >= max_wait:
            raise TimeoutError(f"kie.ai task {task_id} did not complete within {max_wait}s")

        attempt += 1
        await syslog("debug", f"KIEAI poll #{attempt}: GET {url} (elapsed={elapsed:.1f}s)", source="audio")

        try:
            resp = await client.get(url, headers=_auth_headers(api_key))
        except httpx.RequestError as e:
            await syslog("warning", f"KIEAI poll #{attempt} request error: {e}", source="audio")
            await asyncio.sleep(KIEAI_POLL_INTERVAL)
            continue

        await syslog("debug", f"KIEAI poll #{attempt} response: status={resp.status_code}, body={resp.text[:500]}", source="audio")

        if resp.status_code != 200:
            await syslog("warning", f"KIEAI poll #{attempt}: HTTP {resp.status_code}, retrying...", source="audio")
            await asyncio.sleep(KIEAI_POLL_INTERVAL)
            continue

        body = resp.json()
        data = body.get("data") or {}
        state = data.get("state", "")

        if state == "success":
            await syslog("info", f"KIEAI task {task_id} completed successfully after {elapsed:.1f}s ({attempt} polls)", source="audio")
            return data

        if state in ("failed", "error"):
            fail_msg = data.get("failMsg", "Unknown failure")
            fail_code = data.get("failCode", "?")
            raise ValueError(f"kie.ai task failed ({fail_code}): {fail_msg}")

        # Task still processing — wait and retry
        await asyncio.sleep(KIEAI_POLL_INTERVAL)


# ── TTS ──────────────────────────────────────────────────────────────

async def text_to_speech(
    db: AsyncIOMotorDatabase,
    text: str,
    voice: str | None = None,
    provider: str | None = None,
) -> dict:
    """
    Generate audio from text via kie.ai (async task with polling).
    Returns: {"audio_url": "/api/uploads/audio/<file>", "provider": "kieai", "duration_ms": ...}
    """
    await syslog("info", f"TTS START: text_length={len(text)}, voice={voice}", source="audio")
    start = time.time()
    try:
        result = await _tts_kieai(db, text, voice)
        duration_ms = int((time.time() - start) * 1000)
        result["duration_ms"] = duration_ms
        result["provider"] = "kieai"
        await syslog("info", f"TTS COMPLETE: {len(text)} chars -> {result.get('filename', '?')} ({duration_ms}ms)", source="audio")
        return result
    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        await syslog("error", f"TTS FAILED: {type(e).__name__}: {str(e)} ({duration_ms}ms)", source="audio")
        raise


async def _tts_kieai(db: AsyncIOMotorDatabase, text: str, voice: str | None) -> dict:
    """
    kie.ai TTS via async job API with polling:
      1. POST createTask → get taskId
      2. GET getTask/{taskId} in a loop until state == 'success'
      3. Download audio from resultUrls
    """
    api_key = await _get_setting(db, "kieai_api_key")
    if not api_key:
        raise ValueError("kie.ai API key not configured. Set 'kieai_api_key' in System Settings.")

    timeout_str = await _get_setting(db, "tts_timeout")
    max_wait = int(timeout_str) if timeout_str and timeout_str.isdigit() else KIEAI_MAX_WAIT_DEFAULT

    voice = voice or "Rachel"
    filename = f"{uuid.uuid4().hex}.mp3"
    filepath = AUDIO_DIR / filename

    input_data = {
        "text": text,
        "voice": voice,
        "stability": 0.5,
        "similarity_boost": 0.75,
        "style": 0,
        "speed": 1,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        # Step 1: Create task
        task_id = await _create_task(client, api_key, KIEAI_TTS_MODEL, input_data)

        # Step 2: Poll until complete
        task_data = await _poll_task(client, api_key, task_id, max_wait)

        # Step 3: Parse resultJson -> resultUrls
        result_json_str = task_data.get("resultJson", "{}")
        result_json = _parse_kieai_result_json(result_json_str)

        result_urls = result_json.get("resultUrls", [])
        if not result_urls:
            raise ValueError(f"kie.ai task completed but no resultUrls in: {result_json}")

        audio_url = result_urls[0]
        await syslog("debug", f"TTS: downloading audio from {audio_url}", source="audio")

        # Step 4: Download audio
        dl_resp = await client.get(audio_url, follow_redirects=True)
        if dl_resp.status_code != 200:
            raise ValueError(f"Failed to download audio from {audio_url}: HTTP {dl_resp.status_code}")

        audio_bytes = dl_resp.content
        if not audio_bytes or len(audio_bytes) == 0:
            raise ValueError("Downloaded audio file is empty")

        filepath.write_bytes(audio_bytes)
        file_size = len(audio_bytes)
        await syslog("info", f"TTS SUCCESS: {filename} ({file_size} bytes) from task {task_id}", source="audio")

    return {"audio_url": f"/api/uploads/audio/{filename}", "filename": filename, "file_size": file_size}


# ── STT ──────────────────────────────────────────────────────────────

async def speech_to_text(
    db: AsyncIOMotorDatabase,
    audio_data: bytes,
    audio_format: str = "wav",
    provider: str | None = None,
    language: str | None = None,
) -> dict:
    """Transcribe audio to text via kie.ai."""
    await syslog("info", f"STT START: audio_size={len(audio_data)}, format={audio_format}, language={language}", source="audio")
    start = time.time()
    try:
        result = await _stt_kieai(db, audio_data, audio_format, language)
        duration_ms = int((time.time() - start) * 1000)
        result["duration_ms"] = duration_ms
        result["provider"] = "kieai"
        await syslog("info", f"STT COMPLETE: {len(audio_data)} bytes -> {len(result.get('text', ''))} chars ({duration_ms}ms)", source="audio")
        return result
    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        await syslog("error", f"STT FAILED: {type(e).__name__}: {str(e)} ({duration_ms}ms)", source="audio")
        raise


async def _stt_kieai(
    db: AsyncIOMotorDatabase,
    audio_data: bytes,
    audio_format: str = "wav",
    language: str | None = None,
) -> dict:
    """kie.ai STT via async task API: upload audio → createTask → poll recordInfo → text."""
    api_key = await _get_setting(db, "kieai_api_key")
    if not api_key:
        raise ValueError("kie.ai API key not configured. Set 'kieai_api_key' in System Settings.")

    timeout_str = await _get_setting(db, "tts_timeout")
    max_wait = int(timeout_str) if timeout_str and timeout_str.isdigit() else KIEAI_MAX_WAIT_DEFAULT

    ext = audio_format if audio_format in ("wav", "mp3", "webm", "m4a", "ogg", "flac") else "ogg"

    await syslog("debug", f"STT: starting, audio_size={len(audio_data)}, format={ext}", source="audio")

    # Convert unsupported formats to MP3 (kie.ai returns 500 for OGG, WEBM, etc.)
    if ext in FORMATS_NEED_CONVERSION:
        await syslog("debug", f"STT: converting {ext} -> mp3 for kie.ai compatibility", source="audio")
        audio_data, ext = await _convert_audio_to_mp3(audio_data, ext)

    async with httpx.AsyncClient(timeout=30) as client:
        # Step 1: Upload audio to temp hosting to get a public URL
        audio_url = await _upload_temp_audio(client, audio_data, ext)

        # Step 2: Create STT task
        input_data = {
            "audio_url": audio_url,
            "tag_audio_events": False,
            "diarize": False,
        }
        if language:
            input_data["language_code"] = language

        task_id = await _create_task(client, api_key, KIEAI_STT_MODEL, input_data)

        # Step 3: Poll for result
        task_data = await _poll_task(client, api_key, task_id, max_wait)

        # Step 4: Extract text from resultJson.resultObject.text
        result_json_str = task_data.get("resultJson", "{}")
        await syslog("debug", f"STT resultJson raw ({len(str(result_json_str))} chars): {str(result_json_str)[:500]}", source="audio")

        result_json = _parse_kieai_result_json(result_json_str)

        result_obj = result_json.get("resultObject", {})
        if isinstance(result_obj, str):
            try:
                result_obj = json.loads(result_obj)
            except (json.JSONDecodeError, ValueError):
                result_obj = {}

        await syslog("debug", f"STT resultObject keys: {list(result_obj.keys()) if isinstance(result_obj, dict) else type(result_obj)}", source="audio")

        text = result_obj.get("text", "")
        if not text:
            raise ValueError(f"kie.ai STT returned no text. resultJson: {str(result_json)[:500]}")

        detected_lang = result_obj.get("language_code", "")
        await syslog("info", f"STT SUCCESS: {len(audio_data)} bytes -> {len(text)} chars, lang={detected_lang}", source="audio")
        return {"text": text, "language": detected_lang}


# ── Available voices ─────────────────────────────────────────────────

KIEAI_VOICES = [
    "Alice",
    "Bill",
    "Brian",
    "Callum",
    "Charlie",
    "Chris",
    "Daniel",
    "Eric",
    "George",
    "Jessica",
    "Laura",
    "Liam",
    "Lily",
    "Matilda",
    "Rachel",
    "River",
    "Roger",
    "Sarah",
    "Will",
]


def get_available_voices(provider: str = "kieai") -> list[str]:
    return KIEAI_VOICES
