"""Cloud provider: Groq (OpenAI-compatible API)."""
from typing import Any

from app.config import get_settings
from app.llm.base import Completion, LLMProvider
from app.llm.errors import LLMError

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqProvider(LLMProvider):
    name = "groq"

    def __init__(self) -> None:
        self._settings = get_settings()

    @property
    def model(self) -> str:
        return self._settings.groq_model

    async def _complete(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        json_schema: dict[str, Any] | None = None,
    ) -> Completion:
        # The ONLY place where the real key is read, and it is never logged.
        api_key = self._settings.groq_api_key.get_secret_value()
        if not api_key:
            raise LLMError("GROQ_API_KEY is missing in .env.", 500)

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if json_schema:
            # Groq guarantees valid JSON here, but NOT our exact schema.
            # Pydantic validation (in base.py) checks the schema.
            payload["response_format"] = {"type": "json_object"}

        data = await self._post_json(
            GROQ_URL, payload, headers={"Authorization": f"Bearer {api_key}"}
        )
        usage = data.get("usage", {})
        return Completion(
            text=data["choices"][0]["message"]["content"],
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
        )