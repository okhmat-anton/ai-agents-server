"""
Ollama management API — status, start, list/pull/delete models.
"""
import asyncio
import signal
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.config import get_settings
from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.log_service import syslog_bg

router = APIRouter(prefix="/api/ollama", tags=["ollama"])


# ── Schemas ──────────────────────────────────────────────

class OllamaStatus(BaseModel):
    running: bool
    base_url: str
    models_count: int = 0


class OllamaModel(BaseModel):
    name: str
    size: int = 0
    size_hr: str = ""
    parameter_size: str = ""
    quantization: str = ""
    family: str = ""
    modified_at: str = ""
    digest: str = ""


class OllamaModelDetail(BaseModel):
    name: str
    modelfile: str = ""
    parameters: str = ""
    template: str = ""
    system: str = ""
    license: str = ""


class PullRequest(BaseModel):
    model: str  # e.g. "llama3:8b", "qwen2.5-coder:14b"


class ChatRequest(BaseModel):
    model: str
    message: str
    system: str = ""
    temperature: float = 0.7


class PullProgress(BaseModel):
    status: str
    completed: bool = False
    progress: float = 0.0  # 0-100


# ── Helpers ──────────────────────────────────────────────

def _settings():
    return get_settings()


def _size_hr(size_bytes: int) -> str:
    if size_bytes >= 1e9:
        return f"{size_bytes / 1e9:.1f} GB"
    if size_bytes >= 1e6:
        return f"{size_bytes / 1e6:.1f} MB"
    return f"{size_bytes} B"


# ── Endpoints ────────────────────────────────────────────

@router.get("/status", response_model=OllamaStatus)
async def ollama_status(_user: User = Depends(get_current_user)):
    """Check if Ollama is running and how many models are loaded."""
    settings = _settings()
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            if r.status_code == 200:
                models = r.json().get("models", [])
                return OllamaStatus(running=True, base_url=settings.OLLAMA_BASE_URL, models_count=len(models))
    except Exception:
        pass
    return OllamaStatus(running=False, base_url=settings.OLLAMA_BASE_URL)


@router.post("/start")
async def start_ollama(_user: User = Depends(get_current_user)):
    """Attempt to start Ollama via `ollama serve`."""
    settings = _settings()

    # First check if already running
    try:
        async with httpx.AsyncClient(timeout=2) as client:
            r = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            if r.status_code == 200:
                return {"message": "Ollama is already running", "started": False}
    except Exception:
        pass

    # Try to start ollama serve in background
    try:
        proc = await asyncio.create_subprocess_exec(
            "ollama", "serve",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        # Wait a moment for it to start
        await asyncio.sleep(2)

        # Check if it's now running
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                r = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
                if r.status_code == 200:
                    await syslog_bg("info", "Ollama started successfully", source="system")
                    return {"message": "Ollama started successfully", "started": True}
        except Exception:
            pass

        # Still not running — check if binary found but failed
        if proc.returncode is not None:
            await syslog_bg("error", f"Ollama process exited with code {proc.returncode}", source="system")
            raise HTTPException(status_code=500, detail=f"Ollama exited with code {proc.returncode}")

        # Process is running but not responding yet, give more time
        await asyncio.sleep(3)
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                r = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
                if r.status_code == 200:
                    await syslog_bg("info", "Ollama started successfully (delayed)", source="system")
                    return {"message": "Ollama started successfully", "started": True}
        except Exception:
            pass

        raise HTTPException(status_code=500, detail="Ollama started but not responding")

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Ollama binary not found. Install from https://ollama.ai")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start Ollama: {str(e)}")


@router.post("/stop")
async def stop_ollama(_user: User = Depends(get_current_user)):
    """Stop the running Ollama process."""
    settings = _settings()

    # Check if running
    try:
        async with httpx.AsyncClient(timeout=2) as client:
            r = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            if r.status_code != 200:
                return {"message": "Ollama is not running", "stopped": False}
    except Exception:
        return {"message": "Ollama is not running", "stopped": False}

    # Find and kill ollama process
    try:
        proc = await asyncio.create_subprocess_exec(
            "pkill", "-f", "ollama serve",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()

        # Also try via killall as fallback
        proc2 = await asyncio.create_subprocess_exec(
            "pkill", "ollama",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc2.wait()

        await asyncio.sleep(1)

        # Verify it stopped
        try:
            async with httpx.AsyncClient(timeout=2) as client:
                r = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
                if r.status_code == 200:
                    # Still running — try SIGKILL
                    proc3 = await asyncio.create_subprocess_exec(
                        "pkill", "-9", "ollama",
                        stdout=asyncio.subprocess.DEVNULL,
                        stderr=asyncio.subprocess.DEVNULL,
                    )
                    await proc3.wait()
                    await asyncio.sleep(1)
        except Exception:
            pass  # Connection refused = stopped successfully

        await syslog_bg("info", "Ollama stopped", source="system")
        return {"message": "Ollama stopped", "stopped": True}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop Ollama: {str(e)}")


@router.get("/models", response_model=list[OllamaModel])
async def list_models(_user: User = Depends(get_current_user)):
    """List all locally available Ollama models."""
    settings = _settings()
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            r.raise_for_status()
            data = r.json()
    except Exception:
        raise HTTPException(status_code=503, detail="Ollama is not running")

    models = []
    for m in data.get("models", []):
        details = m.get("details", {})
        models.append(OllamaModel(
            name=m.get("name", ""),
            size=m.get("size", 0),
            size_hr=_size_hr(m.get("size", 0)),
            parameter_size=details.get("parameter_size", ""),
            quantization=details.get("quantization_level", ""),
            family=details.get("family", ""),
            modified_at=m.get("modified_at", ""),
            digest=m.get("digest", "")[:12] if m.get("digest") else "",
        ))
    return models


@router.get("/models/{model_name:path}/detail", response_model=OllamaModelDetail)
async def model_detail(model_name: str, _user: User = Depends(get_current_user)):
    """Get detailed info about a specific model."""
    settings = _settings()
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(f"{settings.OLLAMA_BASE_URL}/api/show", json={"name": model_name})
            r.raise_for_status()
            data = r.json()
    except httpx.HTTPStatusError:
        raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")
    except Exception:
        raise HTTPException(status_code=503, detail="Ollama is not running")

    return OllamaModelDetail(
        name=model_name,
        modelfile=data.get("modelfile", ""),
        parameters=data.get("parameters", ""),
        template=data.get("template", ""),
        system=data.get("system", ""),
        license=data.get("license", ""),
    )


@router.post("/models/pull")
async def pull_model(body: PullRequest, _user: User = Depends(get_current_user)):
    """Pull (download) a model from Ollama registry."""
    settings = _settings()
    model_name = body.model

    # Check Ollama is running
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            r.raise_for_status()
    except Exception:
        raise HTTPException(status_code=503, detail="Ollama is not running")

    await syslog_bg("info", f"Pulling model: {model_name}", source="system")

    # Start pull (this can take a long time, we do it async and return immediately)
    try:
        async with httpx.AsyncClient(timeout=600) as client:
            r = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/pull",
                json={"name": model_name, "stream": False},
                timeout=600,
            )
            r.raise_for_status()
    except httpx.ReadTimeout:
        # Very large model — pull is still going
        return {"message": f"Pull of '{model_name}' started (may take a while)", "status": "downloading"}
    except Exception as e:
        await syslog_bg("error", f"Failed to pull model {model_name}: {e}", source="system")
        raise HTTPException(status_code=500, detail=f"Pull failed: {str(e)}")

    await syslog_bg("info", f"Model '{model_name}' pulled successfully", source="system")
    return {"message": f"Model '{model_name}' pulled successfully", "status": "success"}


@router.delete("/models/{model_name:path}")
async def delete_model(model_name: str, _user: User = Depends(get_current_user)):
    """Delete a locally cached model."""
    settings = _settings()
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.delete(
                f"{settings.OLLAMA_BASE_URL}/api/delete",
                json={"name": model_name},
            )
            if r.status_code == 404:
                raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")
            r.raise_for_status()
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=503, detail="Ollama is not running")

    await syslog_bg("info", f"Model '{model_name}' deleted", source="system")
    return {"message": f"Model '{model_name}' deleted"}


@router.post("/models/{model_name:path}/load")
async def load_model(model_name: str, _user: User = Depends(get_current_user)):
    """Load a model into memory (warm up)."""
    settings = _settings()
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/generate",
                json={"model": model_name, "prompt": "", "keep_alive": "10m"},
                timeout=120,
            )
            r.raise_for_status()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")
        raise HTTPException(status_code=500, detail=f"Failed to load model: {e}")
    except Exception:
        raise HTTPException(status_code=503, detail="Ollama is not running")

    await syslog_bg("info", f"Model '{model_name}' loaded into memory", source="system")
    return {"message": f"Model '{model_name}' loaded"}


@router.post("/models/{model_name:path}/unload")
async def unload_model(model_name: str, _user: User = Depends(get_current_user)):
    """Unload a model from memory."""
    settings = _settings()
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/generate",
                json={"model": model_name, "prompt": "", "keep_alive": 0},
                timeout=30,
            )
            r.raise_for_status()
    except Exception:
        raise HTTPException(status_code=503, detail="Ollama is not running")

    # Poll until model is actually evicted from memory (up to 5s)
    for _ in range(10):
        await asyncio.sleep(0.5)
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                r = await client.get(f"{settings.OLLAMA_BASE_URL}/api/ps")
                if r.status_code == 200:
                    names = [m.get("name", "") for m in r.json().get("models", [])]
                    if model_name not in names:
                        break
        except Exception:
            break

    await syslog_bg("info", f"Model '{model_name}' unloaded from memory", source="system")
    return {"message": f"Model '{model_name}' unloaded"}


@router.post("/chat")
async def chat_with_model(body: ChatRequest, _user: User = Depends(get_current_user)):
    """Send a message to a model and get a response (non-streaming)."""
    settings = _settings()
    messages = []
    if body.system:
        messages.append({"role": "system", "content": body.system})
    messages.append({"role": "user", "content": body.message})

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/chat",
                json={
                    "model": body.model,
                    "messages": messages,
                    "stream": False,
                    "options": {"temperature": body.temperature},
                },
                timeout=120,
            )
            r.raise_for_status()
            data = r.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Model '{body.model}' not found")
        raise HTTPException(status_code=500, detail=f"Chat failed: {e}")
    except httpx.ReadTimeout:
        raise HTTPException(status_code=504, detail="Model took too long to respond")
    except Exception:
        raise HTTPException(status_code=503, detail="Ollama is not running")

    msg = data.get("message", {})
    return {
        "role": msg.get("role", "assistant"),
        "content": msg.get("content", ""),
        "model": data.get("model", body.model),
        "total_duration": data.get("total_duration", 0),
        "eval_count": data.get("eval_count", 0),
        "eval_duration": data.get("eval_duration", 0),
    }


@router.get("/running")
async def running_models(_user: User = Depends(get_current_user)):
    """List models currently loaded in memory (running)."""
    settings = _settings()
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{settings.OLLAMA_BASE_URL}/api/ps")
            r.raise_for_status()
            data = r.json()
    except Exception:
        raise HTTPException(status_code=503, detail="Ollama is not running")

    models = []
    for m in data.get("models", []):
        models.append({
            "name": m.get("name", ""),
            "size": m.get("size", 0),
            "size_hr": _size_hr(m.get("size", 0)),
            "size_vram": m.get("size_vram", 0),
            "size_vram_hr": _size_hr(m.get("size_vram", 0)),
            "expires_at": m.get("expires_at", ""),
        })
    return models
