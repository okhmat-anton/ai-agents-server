"""
Audio service: TTS (Text-to-Speech) and STT (Speech-to-Text) via kie.ai.

Provider: kie.ai (ElevenLabs proxy)
 - TTS: https://kie.ai/elevenlabs/text-to-dialogue-v3
 - STT: https://kie.ai/elevenlabs-speech-to-text

API key stored in SystemSettings: kieai_api_key
"""
import os
import uuid
import time
import httpx
from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.mongodb.services import SystemSettingService
from app.services.log_service import syslog


AUDIO_DIR = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))).resolve() / "data" / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)


async def _get_setting(db: AsyncIOMotorDatabase, key: str) -> str | None:
    svc = SystemSettingService(db)
    s = await svc.get_by_key(key)
    return s.value if s else None


# ── TTS ──────────────────────────────────────────────────────────────

async def text_to_speech(
    db: AsyncIOMotorDatabase,
    text: str,
    voice: str | None = None,
    provider: str | None = None,
) -> dict:
    """
    Generate audio from text via kie.ai.
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
    """kie.ai TTS (ElevenLabs proxy): https://kie.ai/elevenlabs/text-to-dialogue-v3"""
    api_key = await _get_setting(db, "kieai_api_key")
    if not api_key:
        raise ValueError("kie.ai API key not configured. Set 'kieai_api_key' in System Settings.")

    voice = voice or "Rachel"  # ElevenLabs default voices
    filename = f"{uuid.uuid4().hex}.mp3"
    filepath = AUDIO_DIR / filename

    url = "https://kie.ai/elevenlabs/text-to-dialogue-v3"
    request_payload = {
        "text": text,
        "voice_id": voice,
        "model_id": "eleven_multilingual_v2",
        "output_format": "mp3_44100_128",
    }
    
    await syslog("debug", f"TTS REQUEST: URL={url}", source="audio")
    await syslog("debug", f"TTS REQUEST: text_length={len(text)}, voice={voice}", source="audio")
    await syslog("debug", f"TTS REQUEST: payload={request_payload}", source="audio")
    await syslog("debug", f"TTS REQUEST: api_key_length={len(api_key) if api_key else 0}, starts_with={api_key[:10] if api_key else 'None'}...", source="audio")

    # kie.ai uses ElevenLabs-compatible API
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=request_payload,
        )
        
        await syslog("debug", f"TTS RESPONSE: status={resp.status_code}", source="audio")
        await syslog("debug", f"TTS RESPONSE: headers={dict(resp.headers)}", source="audio")
        await syslog("debug", f"TTS RESPONSE: content_length={len(resp.content)}", source="audio")
        
        if resp.status_code != 200:
            error_text = resp.text[:1000]
            await syslog("error", f"TTS ERROR: HTTP {resp.status_code}: {error_text}", source="audio")
            raise ValueError(f"kie.ai TTS error: HTTP {resp.status_code}: {error_text}")
        
        # Check content type
        content_type = resp.headers.get("content-type", "")
        await syslog("debug", f"TTS RESPONSE: content-type={content_type}", source="audio")
        
        # If response is JSON, log it (might be error)
        if "application/json" in content_type:
            try:
                json_response = resp.json()
                await syslog("error", f"TTS ERROR: Got JSON instead of audio: {json_response}", source="audio")
                raise ValueError(f"kie.ai returned JSON instead of audio: {json_response}")
            except Exception as e:
                await syslog("debug", f"TTS RESPONSE: Failed to parse as JSON: {e}", source="audio")
        
        # Response is direct audio bytes
        audio_data = resp.content
        if not audio_data or len(audio_data) == 0:
            await syslog("error", f"TTS ERROR: Empty audio data received", source="audio")
            raise ValueError(f"kie.ai returned empty audio data")
        
        filepath.write_bytes(audio_data)
        file_size = len(audio_data)
        await syslog("info", f"TTS SUCCESS: Audio file created: {filename} ({file_size} bytes)", source="audio")

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
    Transcribe audio to text via kie.ai.
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
    """kie.ai STT (ElevenLabs proxy): https://kie.ai/elevenlabs-speech-to-text"""
    api_key = await _get_setting(db, "kieai_api_key")
    if not api_key:
        raise ValueError("kie.ai API key not configured. Set 'kieai_api_key' in System Settings.")

    ext = audio_format if audio_format in ("wav", "mp3", "webm", "m4a", "ogg", "flac") else "wav"
    url = "https://kie.ai/elevenlabs-speech-to-text"
    
    await syslog("debug", f"STT REQUEST: URL={url}", source="audio")
    await syslog("debug", f"STT REQUEST: audio_size={len(audio_data)}, format={ext}, language={language}", source="audio")
    await syslog("debug", f"STT REQUEST: api_key_length={len(api_key) if api_key else 0}", source="audio")

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
        
        await syslog("debug", f"STT RESPONSE: status={resp.status_code}", source="audio")
        await syslog("debug", f"STT RESPONSE: headers={dict(resp.headers)}", source="audio")
        await syslog("debug", f"STT RESPONSE: content_length={len(resp.content)}", source="audio")
        
        if resp.status_code != 200:
            error_text = resp.text[:1000]
            await syslog("error", f"STT ERROR: HTTP {resp.status_code}: {error_text}", source="audio")
            raise ValueError(f"kie.ai STT error: HTTP {resp.status_code}: {error_text}")

        try:
            result = resp.json()
            await syslog("debug", f"STT RESPONSE: json={result}", source="audio")
            text = result.get("text", "")
            await syslog("info", f"STT SUCCESS: Transcribed {len(audio_data)} bytes → {len(text)} chars", source="audio")
            return {"text": text}
        except Exception as e:
            await syslog("error", f"STT ERROR: Failed to parse JSON response: {e}, raw={resp.text[:500]}", source="audio")
            raise ValueError(f"kie.ai STT error: Invalid JSON response: {e}")


# ── Available voices ─────────────────────────────────────────────────

KIEAI_VOICES = [
    "Rachel",
    "Clyde",
    "Domi",
    "Dave",
    "Fin",
    "Sarah",
    "Laura",
    "Charlie",
    "George",
    "Callum",
    "Charlotte",
    "Alice",
    "Matilda",
    "Will",
]


def get_available_voices(provider: str = "kieai") -> list[str]:
    return KIEAI_VOICES
