"""Local provider: Ollama HTTP server."""
from typing import Any

from app.config import get_settings
from app.llm.base import Completion, LLMProvider


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
            "options": {"temperature": temperature},
        }
        if json_schema:
            payload["format"] = json_schema  # Ollama: full JSON Schema

        data = await self._post_json(f"{self._settings.ollama_base_url}/api/chat", payload)
        return Completion(
            text=data["message"]["content"],
            prompt_tokens=data.get("prompt_eval_count", 0),
            completion_tokens=data.get("eval_count", 0),
        )