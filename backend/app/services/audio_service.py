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


MIME_MAP = {
    "ogg": "audio/ogg",
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
    "webm": "audio/webm",
    "m4a": "audio/mp4",
    "flac": "audio/flac",
}


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

async def _create_task(
    client: httpx.AsyncClient,
    api_key: str,
    model: str,
    input_data: dict,
) -> str:
    """Submit a task to kie.ai -> returns taskId."""
    payload = {
        "model": model,
        "input": input_data,
    }

    await syslog("debug", f"KIEAI createTask: model={model}", source="audio")

    resp = await client.post(KIEAI_CREATE_TASK, headers=_auth_headers(api_key), json=payload)
    await syslog("debug", f"KIEAI createTask response: status={resp.status_code}, body={resp.text[:500]}", source="audio")

    if resp.status_code != 200:
        error_text = resp.text[:1000]
        raise ValueError(f"kie.ai createTask error: HTTP {resp.status_code}: {error_text}")

    body = resp.json()
    code = body.get("code")
    if code != 200:
        msg = body.get("msg", "Unknown error")
        raise ValueError(f"kie.ai error ({code}): {msg}")

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
        try:
            result_json = json.loads(result_json_str) if isinstance(result_json_str, str) else result_json_str
        except (json.JSONDecodeError, TypeError):
            raise ValueError(f"kie.ai returned invalid resultJson: {str(result_json_str)[:500]}")

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
        try:
            result_json = json.loads(result_json_str) if isinstance(result_json_str, str) else result_json_str
        except (json.JSONDecodeError, TypeError):
            raise ValueError(f"kie.ai STT returned invalid resultJson: {str(result_json_str)[:500]}")

        result_obj = result_json.get("resultObject", {})
        if isinstance(result_obj, str):
            try:
                result_obj = json.loads(result_obj)
            except (json.JSONDecodeError, ValueError):
                result_obj = {}

        text = result_obj.get("text", "")
        if not text:
            raise ValueError(f"kie.ai STT returned no text. resultJson: {str(result_json)[:500]}")

        detected_lang = result_obj.get("language_code", "")
        await syslog("info", f"STT SUCCESS: {len(audio_data)} bytes -> {len(text)} chars, lang={detected_lang}", source="audio")
        return {"text": text, "language": detected_lang}


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
