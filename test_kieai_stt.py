"""Test kie.ai STT endpoint — send a small audio file."""
import httpx
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from pathlib import Path
import os
import struct
import math


async def get_api_key():
    client = AsyncIOMotorClient("mongodb://agents:mongo_secret_2026@localhost:4717")
    db = client["ai_agents"]
    setting = await db["system_settings"].find_one({"key": "kieai_api_key"})
    client.close()
    return setting["value"] if setting else None


def generate_wav_hello():
    """Generate a tiny WAV file with a sine wave (just to test the endpoint accepts audio)."""
    sample_rate = 16000
    duration = 1.0
    freq = 440
    n_samples = int(sample_rate * duration)
    samples = [int(32767 * 0.5 * math.sin(2 * math.pi * freq * i / sample_rate)) for i in range(n_samples)]
    
    data = struct.pack(f"<{n_samples}h", *samples)
    # WAV header
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + len(data), b"WAVE",
        b"fmt ", 16, 1, 1, sample_rate, sample_rate * 2, 2, 16,
        b"data", len(data),
    )
    return header + data


def test_stt(api_key):
    headers = {"Authorization": f"Bearer {api_key}"}
    wav_data = generate_wav_hello()
    print(f"Generated WAV: {len(wav_data)} bytes")

    # Also check if there's a real voice file in chat_media
    chat_media = Path("data/chat_media")
    ogg_files = list(chat_media.glob("*.ogg")) if chat_media.exists() else []
    print(f"Found {len(ogg_files)} OGG files in chat_media/")
    
    # Test URLs
    urls = [
        "https://kie.ai/elevenlabs-speech-to-text",
        "https://api.kie.ai/elevenlabs-speech-to-text",
        "https://api.kie.ai/api/v1/elevenlabs-speech-to-text",
        "https://api.kie.ai/api/v1/stt",
        "https://api.kie.ai/api/v1/speech-to-text",
        "https://api.kie.ai/api/v1/audio/transcribe",
    ]

    with httpx.Client(timeout=30) as c:
        print("\n=== Testing STT endpoints with WAV ===")
        for url in urls:
            try:
                files = {"audio": ("test.wav", wav_data, "audio/wav")}
                resp = c.post(url, headers=headers, files=files)
                print(f"POST {url}")
                print(f"  -> {resp.status_code}: {resp.text[:500]}")
            except Exception as e:
                print(f"POST {url}")
                print(f"  -> ERROR: {e}")
            print()

        # Also try with "file" field name instead of "audio"
        print("=== Try 'file' field name ===")
        for url in urls[:3]:
            try:
                files = {"file": ("test.wav", wav_data, "audio/wav")}
                resp = c.post(url, headers=headers, files=files)
                print(f"POST {url} (field=file)")
                print(f"  -> {resp.status_code}: {resp.text[:500]}")
            except Exception as e:
                print(f"POST {url}")
                print(f"  -> ERROR: {e}")
            print()

        # Try async job approach for STT (like TTS)
        print("=== Try async createTask for STT ===")
        # Maybe STT also uses the job API
        stt_models = [
            "elevenlabs/speech-to-text",
            "openai/whisper-1",
            "elevenlabs/scribe_v1",
        ]
        for model in stt_models:
            # For audio jobs, we'd need to upload... Let's try just the model query
            try:
                resp = c.post(
                    "https://api.kie.ai/api/v1/jobs/createTask",
                    headers={**headers, "Content-Type": "application/json"},
                    json={"model": model, "input": {"text": "test"}},
                )
                print(f"createTask model={model}")
                print(f"  -> {resp.status_code}: {resp.text[:300]}")
            except Exception as e:
                print(f"  -> ERROR: {e}")
            print()

        # If we have a real OGG, try it too
        if ogg_files:
            ogg_path = ogg_files[0]
            ogg_data = ogg_path.read_bytes()
            print(f"\n=== Testing with real OGG file: {ogg_path.name} ({len(ogg_data)} bytes) ===")
            for url in urls[:3]:
                try:
                    files = {"audio": ("voice.ogg", ogg_data, "audio/ogg")}
                    resp = c.post(url, headers=headers, files=files)
                    print(f"POST {url}")
                    print(f"  -> {resp.status_code}: {resp.text[:500]}")
                except Exception as e:
                    print(f"  -> ERROR: {e}")
                print()


if __name__ == "__main__":
    api_key = asyncio.run(get_api_key())
    print(f"API key: len={len(api_key) if api_key else 0}")
    print()
    test_stt(api_key)
