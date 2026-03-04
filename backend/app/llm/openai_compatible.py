import httpx
import json
from typing import AsyncIterator
from app.llm.base import LLMProvider, Message, GenerationParams, LLMResponse, ModelInfo


class OpenAICompatibleProvider:
    """Provider for LM Studio, llama.cpp server, text-generation-webui, etc."""

    def __init__(self, base_url: str = "http://localhost:1234", api_key: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or "no-key"

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def chat(self, model: str, messages: list[Message], params: GenerationParams) -> LLMResponse:
        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": params.temperature,
            "top_p": params.top_p,
            "max_tokens": params.max_tokens,
            "stream": False,
        }
        if params.stop:
            payload["stop"] = params.stop

        async with httpx.AsyncClient(timeout=300) as client:
            resp = await client.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                headers=self._headers(),
            )
            resp.raise_for_status()
            data = resp.json()

        choice = data.get("choices", [{}])[0]
        usage = data.get("usage", {})
        return LLMResponse(
            content=choice.get("message", {}).get("content", ""),
            model=model,
            total_tokens=usage.get("total_tokens", 0),
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
        )

    async def stream(self, model: str, messages: list[Message], params: GenerationParams) -> AsyncIterator[str]:
        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": params.temperature,
            "top_p": params.top_p,
            "max_tokens": params.max_tokens,
            "stream": True,
        }
        if params.stop:
            payload["stop"] = params.stop

        async with httpx.AsyncClient(timeout=300) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                headers=self._headers(),
            ) as resp:
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        chunk = line[6:]
                        if chunk == "[DONE]":
                            break
                        data = json.loads(chunk)
                        delta = data.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content

    async def list_models(self) -> list[ModelInfo]:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{self.base_url}/v1/models", headers=self._headers())
            resp.raise_for_status()
            data = resp.json()

        return [
            ModelInfo(name=m.get("id", "unknown"))
            for m in data.get("data", [])
        ]

    async def check_connection(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.base_url}/v1/models", headers=self._headers())
                return resp.status_code == 200
        except Exception:
            return False

    async def embeddings(self, text: str, model: str = "text-embedding-nomic-embed-text-v1.5") -> list[float]:
        payload = {"input": text, "model": model}
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.base_url}/v1/embeddings",
                json=payload,
                headers=self._headers(),
            )
            resp.raise_for_status()
            data = resp.json()
        return data.get("data", [{}])[0].get("embedding", [])
