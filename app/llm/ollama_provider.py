"""Local provider: Ollama HTTP server."""
from typing import Any

from app.config import get_settings
from app.llm.base import Completion, LLMProvider

# Context window requested from Ollama (prompt + answer, in tokens).
# Without it, Ollama uses a small default and silently drops the start of long prompts.
# 8192 tokens costs roughly 0.5 GB of extra VRAM for qwen2.5:7b.
# TODO: move to Settings (app/config.py) once we have seen that file.
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