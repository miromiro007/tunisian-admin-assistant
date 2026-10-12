"""Local provider: Ollama HTTP server."""
import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.config import get_settings
from app.llm.base import Completion, LLMProvider, StreamChunk
from app.llm.errors import LLMError

logger = logging.getLogger(__name__)

# Context window requested from Ollama (prompt + answer, in tokens).
# Without it, Ollama uses a small default and silently drops the start of long prompts.
OLLAMA_NUM_CTX = 8192


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(self) -> None:
        self._settings = get_settings()

    @property
    def model(self) -> str:
        return self._settings.ollama_model

    async def _complete(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        json_schema: dict[str, Any] | None = None,
    ) -> Completion:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature, "num_ctx": OLLAMA_NUM_CTX},
        }
        if json_schema:
            payload["format"] = json_schema  # Ollama: full JSON Schema

        data = await self._post_json(f"{self._settings.ollama_base_url}/api/chat", payload)
        return Completion(
            text=data["message"]["content"],
            prompt_tokens=data.get("prompt_eval_count", 0),
            completion_tokens=data.get("eval_count", 0),
        )

    async def stream_messages(
        self, messages: list[dict[str, str]], temperature: float
    ) -> AsyncIterator[StreamChunk]:
        """Real streaming: Ollama sends one JSON object per line while it generates."""
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {"temperature": temperature, "num_ctx": OLLAMA_NUM_CTX},
        }
        url = f"{self._settings.ollama_base_url}/api/chat"
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                async with client.stream("POST", url, json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        data = json.loads(line)
                        if "error" in data:
                            logger.error("[ollama] stream error: %s", data["error"])
                            raise LLMError("ollama returned an error while streaming.", 502)
                        if data.get("done"):
                            yield StreamChunk(
                                "", done=True,
                                prompt_tokens=data.get("prompt_eval_count", 0),
                                completion_tokens=data.get("eval_count", 0),
                            )
                            return
                        text = data.get("message", {}).get("content", "")
                        if text:
                            yield StreamChunk(text)
        except httpx.ConnectError:
            logger.error("[ollama] cannot connect to %s", url)
            raise LLMError("ollama is not reachable.", 503)
        except httpx.TimeoutException:
            logger.error("[ollama] timeout while streaming")
            raise LLMError("ollama took too long to answer.", 504)
        except httpx.HTTPStatusError as exc:
            logger.error("[ollama] HTTP %s while streaming", exc.response.status_code)
            raise LLMError(f"ollama error {exc.response.status_code}.", 502)
        except json.JSONDecodeError:
            logger.error("[ollama] invalid line in the stream")
            raise LLMError("ollama sent an invalid stream.", 502)