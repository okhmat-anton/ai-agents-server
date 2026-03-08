"""
Audio API: TTS (Text-to-Speech) and STT (Speech-to-Text) endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_mongodb
from app.core.dependencies import get_current_user
from app.services.audio_service import (
    text_to_speech, speech_to_text,
    get_available_voices, OPENAI_VOICES, MINIMAX_VOICES,
)

router = APIRouter(prefix="/api/audio", tags=["audio"])


# ── Schemas ──────────────────────────────────────────────────────────

class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = None
    provider: Optional[str] = None  # openai | minimax


class TTSResponse(BaseModel):
    audio_url: str
    filename: str
    provider: str
    duration_ms: int


class STTResponse(BaseModel):
    text: str
    provider: str
    duration_ms: int
    provider_note: Optional[str] = None


class VoicesResponse(BaseModel):
    openai: list[str]
    minimax: list[str]


# ── Endpoints ────────────────────────────────────────────────────────

@router.post("/tts", response_model=TTSResponse)
async def generate_speech(
    body: TTSRequest,
    _user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Generate speech audio from text (TTS)."""
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    if len(body.text) > 10000:
        raise HTTPException(status_code=400, detail="Text too long (max 10000 chars)")

    try:
        result = await text_to_speech(
            db=db,
            text=body.text,
            voice=body.voice,
            provider=body.provider,
        )
        return TTSResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS error: {e}")


@router.post("/stt", response_model=STTResponse)
async def recognize_speech(
    file: UploadFile = File(...),
    provider: Optional[str] = Form(None),
    language: Optional[str] = Form(None),
    _user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Recognize speech from audio file (STT)."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No audio file provided")

    # Determine format from filename
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "wav"

    audio_data = await file.read()
    if not audio_data:
        raise HTTPException(status_code=400, detail="Empty audio file")
    if len(audio_data) > 25 * 1024 * 1024:  # 25MB limit (OpenAI)
        raise HTTPException(status_code=400, detail="Audio file too large (max 25MB)")

    try:
        result = await speech_to_text(
            db=db,
            audio_data=audio_data,
            audio_format=ext,
            provider=provider,
            language=language,
        )
        return STTResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"STT error: {e}")


@router.get("/voices", response_model=VoicesResponse)
async def list_voices(
    _user=Depends(get_current_user),
):
    """List available TTS voices for each provider."""
    return VoicesResponse(
        openai=OPENAI_VOICES,
        minimax=MINIMAX_VOICES,
    )


@router.post("/tts-message/{message_id}")
async def generate_speech_for_message(
    message_id: str,
    voice: Optional[str] = None,
    provider: Optional[str] = None,
    _user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    """Generate TTS audio for an existing chat message and attach it."""
    from app.mongodb.services import ChatMessageService
    msg_svc = ChatMessageService(db)
    msg = await msg_svc.get_by_id(message_id)
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    if not msg.content.strip():
        raise HTTPException(status_code=400, detail="Message has no text content")

    try:
        result = await text_to_speech(db=db, text=msg.content, voice=voice, provider=provider)
        # Attach audio_url to the message
        await msg_svc.update(msg.id, {"audio_url": result["audio_url"]})
        return {
            "audio_url": result["audio_url"],
            "provider": result["provider"],
            "duration_ms": result["duration_ms"],
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS error: {e}")
