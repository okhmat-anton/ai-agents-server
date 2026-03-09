"""
kie.ai LLM provider.

Supports GPT-5.2, Gemini 3.1 Pro, Gemini 3 Pro via OpenAI-compatible format.
Key difference: model name is in the URL path, NOT in the request body.
  e.g. https://api.kie.ai/gemini-3.1-pro/v1/chat/completions

Auth via Bearer token (Authorization header).
"""
import httpx
import json
from typing import AsyncIterator
from app.llm.base import LLMProvider, Message, GenerationParams, LLMResponse, ModelInfo


# Available kie.ai models
KIEAI_MODELS = [
    {"id": "gpt-5-2", "name": "GPT-5.2", "context": 128000, "supports_vision": True},
    {"id": "gemini-3.1-pro", "name": "Gemini 3.1 Pro", "context": 1000000, "supports_vision": True},
    {"id": "gemini-3-pro", "name": "Gemini 3 Pro", "context": 1000000, "supports_vision": True},
]

KIEAI_BASE_URL = "https://api.kie.ai"


class KieAIProvider:
    """Provider for kie.ai models (GPT-5.2, Gemini 3.1 Pro, Gemini 3 Pro).

    kie.ai uses OpenAI-compatible Chat Completions API but the model name
    is part of the URL path, not the request body:
      POST https://api.kie.ai/{model}/v1/chat/completions
    """

    def __init__(self, api_key: str, base_url: str = KIEAI_BASE_URL, timeout: int = 300):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _endpoint(self, model: str) -> str:
        """Build the endpoint URL with model in path."""
        return f"{self.base_url}/{model}/v1/chat/completions"

    def _build_messages(self, messages: list[Message]) -> list[dict]:
        """Convert Message objects to API format."""
        return [{"role": m.role, "content": m.content} for m in messages]

    async def chat(self, model: str, messages: list[Message], params: GenerationParams) -> LLMResponse:
        payload = {
            "messages": self._build_messages(messages),
            "stream": False,
        }
        if params.max_tokens:
            payload["max_tokens"] = params.max_tokens

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                self._endpoint(model),
                json=payload,
                headers=self._headers(),
            )
            resp.raise_for_status()
            data = resp.json()

        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        content = message.get("content", "")
        usage = data.get("usage", {})

        return LLMResponse(
            content=content,
            model=data.get("model", model),
            total_tokens=usage.get("total_tokens", 0),
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
        )

    async def stream(self, model: str, messages: list[Message], params: GenerationParams) -> AsyncIterator[str]:
        payload = {
            "messages": self._build_messages(messages),
            "stream": True,
        }
        if params.max_tokens:
            payload["max_tokens"] = params.max_tokens

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream(
                "POST",
                self._endpoint(model),
                json=payload,
                headers=self._headers(),
            ) as resp:
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        chunk = line[6:]
                        if chunk == "[DONE]":
                            break
                        try:
                            data = json.loads(chunk)
                            delta = data.get("choices", [{}])[0].get("delta", {})
                            # kie.ai sends reasoning in reasoning_content
                            # and actual content in content
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue

    async def list_models(self) -> list[ModelInfo]:
        """Return well-known kie.ai models (no list API available)."""
        return [ModelInfo(name=m["id"]) for m in KIEAI_MODELS]

    async def check_connection(self) -> bool:
        """Test connection by sending a minimal request to a known model."""
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    self._endpoint("gemini-3-pro"),
                    json={
                        "messages": [{"role": "user", "content": "hi"}],
                        "stream": False,
                    },
                    headers=self._headers(),
                )
                return resp.status_code == 200
        except Exception:
            return False

    async def embeddings(self, text: str, model: str = "") -> list[float]:
        """kie.ai doesn't support embeddings."""
        raise NotImplementedError("kie.ai does not provide an embeddings API")
