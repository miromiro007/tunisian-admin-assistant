"""Abstract provider: the common 'plug shape' for every LLM backend."""
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import httpx
from pydantic import ValidationError

from app.llm.errors import LLMError
from app.llm.prompts import ANALYZE_SYSTEM_PROMPT, SYSTEM_PROMPT
from app.schemas import AnalyzeResponse, ChatResponse, QuestionAnalysis

logger = logging.getLogger(__name__)


@dataclass
class Completion:
    """Provider-neutral result of one LLM call."""

    text: str
    prompt_tokens: int
    completion_tokens: int


class LLMProvider(ABC):
    """Every provider must implement `model` and `_complete`."""

    name: str = ""  # "ollama" or "groq"

    @property
    @abstractmethod
    def model(self) -> str:
        """Name of the model used by this provider."""

    @abstractmethod
    async def _complete(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        json_schema: dict[str, Any] | None = None,
    ) -> Completion:
        """Provider-specific HTTP call. This is the ONLY part that differs."""

    # ---------- shared logic (written once) ----------

    async def _post_json(
        self, url: str, payload: dict[str, Any], headers: dict[str, str] | None = None
    ) -> dict[str, Any]:
        """POST JSON and convert every failure into a clean LLMError."""
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
        except httpx.ConnectError:
            logger.error("[%s] cannot connect to %s", self.name, url)
            raise LLMError(f"{self.name} is not reachable.", 503)
        except httpx.TimeoutException:
            logger.error("[%s] timeout", self.name)
            raise LLMError(f"{self.name} took too long to answer.", 504)
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            logger.error("[%s] HTTP %s: %s", self.name, status, exc.response.text)
            if status == 429:
                raise LLMError(f"{self.name} rate limit reached. Retry later.", 429)
            if status in (401, 403):
                raise LLMError(f"{self.name} rejected the credentials (check the API key).", 502)
            raise LLMError(f"{self.name} error {status}.", 502)

    async def chat(self, question: str, temperature: float) -> ChatResponse:
        """Free-text answer."""
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ]
        start = time.perf_counter()
        result = await self._complete(messages, temperature)
        latency_ms = int((time.perf_counter() - start) * 1000)

        logger.info(
            "chat ok provider=%s model=%s in=%d out=%d latency=%dms",
            self.name, self.model, result.prompt_tokens, result.completion_tokens, latency_ms,
        )
        return ChatResponse(
            answer=result.text,
            provider=self.name,
            model=self.model,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            latency_ms=latency_ms,
        )

    async def analyze(self, question: str) -> AnalyzeResponse:
        """Structured answer, validated with Pydantic."""
        messages = [
            {"role": "system", "content": ANALYZE_SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ]
        start = time.perf_counter()
        result = await self._complete(
            messages, 0, QuestionAnalysis.model_json_schema()
        )
        latency_ms = int((time.perf_counter() - start) * 1000)

        # NEVER trust the LLM output: parse AND validate it.
        try:
            analysis = QuestionAnalysis.model_validate_json(result.text)
        except ValidationError as exc:
            logger.error(
                "[%s] invalid structure (%d errors) raw=%s",
                self.name, exc.error_count(), result.text,
            )
            raise LLMError("The model returned an invalid structure.", 502)

        logger.info(
            "analyze ok provider=%s theme=%s in=%d out=%d latency=%dms",
            self.name, analysis.theme, result.prompt_tokens, result.completion_tokens, latency_ms,
        )
        return AnalyzeResponse(
            analysis=analysis,
            provider=self.name,
            model=self.model,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            latency_ms=latency_ms,
        )
    async def complete_messages(
        self, messages: list[dict[str, str]], temperature: float
    ) -> Completion:
        """Public entry point for services (like RAG) that build their own messages."""
        return await self._complete(messages, temperature)  