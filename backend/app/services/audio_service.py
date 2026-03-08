"""
Audio service: TTS (Text-to-Speech) and STT (Speech-to-Text) via kie.ai.

kie.ai API is ASYNC:
  1. POST /api/v1/jobs/createTask  → {taskId}
  2. GET  /api/v1/jobs/getTask/{taskId}  → poll until state == "success"
  3. Download audio from resultUrls

API key stored in SystemSettings: kieai_api_key
"""
import json
import os
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
KIEAI_GET_TASK = f"{KIEAI_API_BASE}/getTask"  # + /{taskId}

KIEAI_TTS_MODEL = "elevenlabs/text-to-speech-turbo-2-5"
KIEAI_STT_MODEL = "elevenlabs/speech-to-text"

KIEAI_POLL_INTERVAL = 2.5   # seconds between status checks
KIEAI_MAX_WAIT_DEFAULT = 120  # default max seconds to wait for result


async def _get_setting(db: AsyncIOMotorDatabase, key: str) -> str | None:
    svc = SystemSettingService(db)
    s = await svc.get_by_key(key)
    return s.value if s else None


def _auth_headers(api_key: str) -> dict:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


# ── Generic kie.ai task helpers ──────────────────────────────────────

async def _create_task(client: httpx.AsyncClient, api_key: str, model: str, input_data: dict) -> str:
    """Submit a task to kie.ai → returns taskId."""
    payload = {
        "model": model,
        "input": input_data,
    }
    await syslog("debug", f"KIEAI createTask: model={model}, input_keys={list(input_data.keys())}", source="audio")

    resp = await client.post(KIEAI_CREATE_TASK, headers=_auth_headers(api_key), json=payload)
    await syslog("debug", f"KIEAI createTask response: status={resp.status_code}", source="audio")

    if resp.status_code != 200:
        error_text = resp.text[:1000]
        await syslog("error", f"KIEAI createTask error: HTTP {resp.status_code}: {error_text}", source="audio")
        raise ValueError(f"kie.ai createTask error: HTTP {resp.status_code}: {error_text}")

    body = resp.json()
    code = body.get("code")
    if code != 200:
        msg = body.get("msg", "Unknown error")
        await syslog("error", f"KIEAI createTask failed: code={code}, msg={msg}", source="audio")
        raise ValueError(f"kie.ai error ({code}): {msg}")

    task_id = (body.get("data") or {}).get("taskId")
    if not task_id:
        raise ValueError(f"kie.ai createTask returned no taskId: {body}")

    await syslog("info", f"KIEAI task created: {task_id}", source="audio")
    return task_id


async def _poll_task(client: httpx.AsyncClient, api_key: str, task_id: str, max_wait: int = KIEAI_MAX_WAIT_DEFAULT) -> dict:
    """Poll kie.ai until task completes. Returns task data dict."""
    poll_url = f"{KIEAI_GET_TASK}/{task_id}"
    headers = _auth_headers(api_key)
    start = time.time()

    while True:
        elapsed = time.time() - start
        if elapsed > max_wait:
            raise TimeoutError(f"kie.ai task {task_id} did not complete within {max_wait}s")

        await asyncio.sleep(KIEAI_POLL_INTERVAL)

        try:
            resp = await client.get(poll_url, headers=headers)
        except httpx.RequestError as e:
            await syslog("warning", f"KIEAI poll network error (will retry): {e}", source="audio")
            continue

        if resp.status_code != 200:
            await syslog("warning", f"KIEAI poll HTTP {resp.status_code} (will retry)", source="audio")
            continue

        body = resp.json()
        task_data = body.get("data") or {}
        state = task_data.get("state", "unknown")
        await syslog("debug", f"KIEAI poll {task_id}: state={state} ({elapsed:.1f}s)", source="audio")

        if state == "success":
            return task_data
        elif state in ("fail", "failed", "error"):
            fail_msg = task_data.get("failMsg", "Unknown failure")
            fail_code = task_data.get("failCode", "?")
            raise ValueError(f"kie.ai task failed ({fail_code}): {fail_msg}")
        # else: still processing — continue polling


# ── TTS ──────────────────────────────────────────────────────────────

async def text_to_speech(
    db: AsyncIOMotorDatabase,
    text: str,
    voice: str | None = None,
    provider: str | None = None,
) -> dict:
    """
    Generate audio from text via kie.ai (async task).
    Returns: {"audio_url": "/api/uploads/audio/<file>", "provider": "kieai", "duration_ms": ...}
    """
    await syslog("info", f"TTS START: text_length={len(text)}, voice={voice}", source="audio")
    start = time.time()
    try:
        result = await _tts_kieai(db, text, voice)
        duration_ms = int((time.time() - start) * 1000)
        result["duration_ms"] = duration_ms
        result["provider"] = "kieai"
        await syslog("info", f"TTS COMPLETE: {len(text)} chars → {result.get('filename', '?')} ({duration_ms}ms)", source="audio")
        return result
    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        await syslog("error", f"TTS FAILED: {type(e).__name__}: {str(e)} ({duration_ms}ms)", source="audio")
        raise


async def _tts_kieai(db: AsyncIOMotorDatabase, text: str, voice: str | None) -> dict:
    """
    kie.ai TTS via async job API:
      1. POST createTask with model=elevenlabs/text-to-speech-turbo-2-5
      2. Poll getTask/{taskId} every 2.5s
      3. Download audio from resultUrls
    """
    api_key = await _get_setting(db, "kieai_api_key")
    if not api_key:
        raise ValueError("kie.ai API key not configured. Set 'kieai_api_key' in System Settings.")

    # Read configurable timeout
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

    await syslog("debug", f"TTS: submitting task, voice={voice}, text_length={len(text)}, max_wait={max_wait}s", source="audio")

    async with httpx.AsyncClient(timeout=30) as client:
        # Step 1: Create task
        task_id = await _create_task(client, api_key, KIEAI_TTS_MODEL, input_data)

        # Step 2: Poll until ready
        task_data = await _poll_task(client, api_key, task_id, max_wait=max_wait)

        # Step 3: Extract audio URL from resultJson and download
        result_json_str = task_data.get("resultJson", "{}")
        try:
            result_json = json.loads(result_json_str) if isinstance(result_json_str, str) else result_json_str
        except (json.JSONDecodeError, TypeError):
            raise ValueError(f"kie.ai returned invalid resultJson: {result_json_str[:500]}")

        result_urls = result_json.get("resultUrls", [])
        if not result_urls:
            raise ValueError(f"kie.ai task completed but no resultUrls: {result_json}")

        audio_url = result_urls[0]
        await syslog("debug", f"TTS: downloading audio from {audio_url}", source="audio")

        # Download the audio file
        dl_resp = await client.get(audio_url, follow_redirects=True)
        if dl_resp.status_code != 200:
            raise ValueError(f"Failed to download audio from {audio_url}: HTTP {dl_resp.status_code}")

        audio_data = dl_resp.content
        if not audio_data or len(audio_data) == 0:
            raise ValueError("Downloaded audio file is empty")

        filepath.write_bytes(audio_data)
        file_size = len(audio_data)
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
    """
    Transcribe audio to text via kie.ai (async task).
    Returns: {"text": "...", "provider": "kieai", "duration_ms": ..., "language": "..."}
    """
    await syslog("info", f"STT START: audio_size={len(audio_data)}, format={audio_format}, language={language}", source="audio")
    start = time.time()
    try:
        result = await _stt_kieai(db, audio_data, audio_format, language)
        duration_ms = int((time.time() - start) * 1000)
        result["duration_ms"] = duration_ms
        result["provider"] = "kieai"
        await syslog("info", f"STT COMPLETE: {len(audio_data)} bytes → {len(result.get('text', ''))} chars ({duration_ms}ms)", source="audio")
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
    """
    kie.ai STT via async job API:
      1. POST createTask with model=elevenlabs/speech-to-text
      2. Poll getTask/{taskId} every 2.5s
      3. Extract transcribed text from result
    """
    api_key = await _get_setting(db, "kieai_api_key")
    if not api_key:
        raise ValueError("kie.ai API key not configured. Set 'kieai_api_key' in System Settings.")

    # For STT we need to upload audio. kie.ai jobs API accepts JSON input,
    # so we first save audio to a temp file, upload it to get a URL, then submit.
    # If kie.ai STT model doesn't exist in jobs API, fall back to direct endpoint.
    # For now, try using the direct ElevenLabs-proxy endpoint as fallback.

    ext = audio_format if audio_format in ("wav", "mp3", "webm", "m4a", "ogg", "flac") else "wav"
    url = "https://kie.ai/elevenlabs-speech-to-text"

    await syslog("debug", f"STT: direct request to {url}, audio_size={len(audio_data)}, format={ext}", source="audio")

    async with httpx.AsyncClient(timeout=120) as client:
        files = {"audio": (f"audio.{ext}", audio_data, f"audio/{ext}")}
        data = {}
        if language:
            data["language"] = language

        resp = await client.post(
            url,
            headers={"Authorization": f"Bearer {api_key}"},
            files=files,
            data=data,
        )

        await syslog("debug", f"STT RESPONSE: status={resp.status_code}, content_type={resp.headers.get('content-type', 'N/A')}", source="audio")

        if resp.status_code != 200:
            error_text = resp.text[:1000]
            await syslog("error", f"STT ERROR: HTTP {resp.status_code}: {error_text}", source="audio")
            raise ValueError(f"kie.ai STT error: HTTP {resp.status_code}: {error_text}")

        try:
            result = resp.json()
            text = result.get("text", "")
            await syslog("info", f"STT SUCCESS: {len(audio_data)} bytes → {len(text)} chars", source="audio")
            return {"text": text}
        except Exception as e:
            await syslog("error", f"STT ERROR: Invalid JSON: {e}, raw={resp.text[:500]}", source="audio")
            raise ValueError(f"kie.ai STT error: Invalid JSON response: {e}")


# ── Available voices ─────────────────────────────────────────────────

KIEAI_VOICES = [
    "Rachel",
    "Aria",
    "Roger",
    "Sarah",
    "Laura",
    "Charlie",
    "George",
    "Callum",
    "River",
    "Liam",
    "Charlotte",
    "Alice",
    "Matilda",
    "Will",
    "Jessica",
    "Eric",
    "Chris",
    "Brian",
    "Daniel",
    "Lily",
    "Bill",
]


def get_available_voices(provider: str = "kieai") -> list[str]:
    return KIEAI_VOICES
