"""Local embedding provider: Ollama /api/embed (model bge-m3 by default)."""
import asyncio
import logging
from typing import Any

import httpx

from app.config import get_settings
from app.embeddings.base import EmbeddingProvider
from app.embeddings.errors import EmbeddingError

logger = logging.getLogger(__name__)


class OllamaEmbeddingProvider(EmbeddingProvider):
    name = "ollama"

    def __init__(
        self,
        transport: httpx.AsyncBaseTransport | None = None,
        retry_base_delay: float = 1.0,
    ) -> None:
        self._settings = get_settings()
        # `transport` lets tests plug a fake server instead of the real network.
        self._transport = transport
        # Seconds to wait before the first retry; doubles after each failure.
        self._retry_base_delay = retry_base_delay

    @property
    def model(self) -> str:
        return self._settings.embedding_model

    @property
    def dimensions(self) -> int:
        return self._settings.embedding_dimensions

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        # An empty text gives a meaningless vector (or an error): refuse it early.
        for index, text in enumerate(texts):
            if not text.strip():
                raise EmbeddingError(f"Text #{index} is empty and cannot be embedded.", 400)

        batch_size = self._settings.embedding_batch_size
        vectors: list[list[float]] = []
        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            vectors.extend(await self._embed_batch(batch))
            logger.debug("embedded %d/%d texts", len(vectors), len(texts))
        return vectors

    async def embed_query(self, text: str) -> list[float]:
        # bge-m3 needs no special prefix. A model like multilingual-e5 would need
        # "query: " here and "passage: " in embed_documents. That difference stays hidden here.
        return (await self.embed_documents([text]))[0]

    async def _embed_batch(self, batch: list[str]) -> list[list[float]]:
        """Embed one batch and validate what comes back."""
        data = await self._post_json(
            f"{self._settings.ollama_base_url}/api/embed",
            {"model": self.model, "input": batch},
        )
        vectors = data.get("embeddings")
        if not isinstance(vectors, list) or len(vectors) != len(batch):
            raise EmbeddingError("ollama returned an unexpected number of vectors.", 502)
        for vector in vectors:
            if len(vector) != self.dimensions:
                raise EmbeddingError(
                    f"Expected {self.dimensions} dimensions but the model returned "
                    f"{len(vector)}. Check EMBEDDING_MODEL, EMBEDDING_DIMENSIONS and the "
                    "vector(N) column of the database.",
                    500,
                )
        return vectors

    async def _post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        """POST JSON, retry temporary failures, convert every failure into EmbeddingError."""
        max_attempts = max(1, self._settings.embedding_max_retries + 1)
        last_error = EmbeddingError("Embedding request failed.", 502)

        for attempt in range(1, max_attempts + 1):
            try:
                async with httpx.AsyncClient(
                    timeout=self._settings.embedding_timeout_seconds,
                    transport=self._transport,
                ) as client:
                    response = await client.post(url, json=payload)
                    response.raise_for_status()
                    return response.json()
            except httpx.ConnectError:
                last_error = EmbeddingError(f"{self.name} is not reachable.", 503)
            except httpx.TimeoutException:
                last_error = EmbeddingError(f"{self.name} took too long to answer.", 504)
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if status == 404:  # permanent: retrying will not help
                    raise EmbeddingError(
                        f"Model '{self.model}' not found in {self.name}. "
                        f"Run: ollama pull {self.model}",
                        502,
                    )
                if status < 500:  # other 4xx errors are permanent too
                    raise EmbeddingError(f"{self.name} error {status}.", 502)
                last_error = EmbeddingError(f"{self.name} error {status}.", 502)

            logger.warning(
                "[%s] attempt %d/%d failed: %s", self.name, attempt, max_attempts, last_error
            )
            if attempt < max_attempts:
                await asyncio.sleep(self._retry_base_delay * 2 ** (attempt - 1))

        raise last_error