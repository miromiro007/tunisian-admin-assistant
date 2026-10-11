"""Tests for the embedding provider, with a FAKE Ollama (no network, no GPU needed).

Run from the project root (venv activated):
    python -m pytest tests -v
"""
import asyncio
import json
from collections.abc import Callable, Iterator

import httpx
import pytest

from app.config import get_settings
from app.embeddings.errors import EmbeddingError
from app.embeddings.factory import get_embedding_provider
from app.embeddings.ollama_embedder import OllamaEmbeddingProvider

DIMENSIONS = 4  # tiny vectors keep the tests readable


@pytest.fixture(autouse=True)
def small_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Use small test settings; get_settings() is cached, so clear the cache around each test."""
    monkeypatch.setenv("EMBEDDING_DIMENSIONS", str(DIMENSIONS))
    monkeypatch.setenv("EMBEDDING_BATCH_SIZE", "32")
    monkeypatch.setenv("EMBEDDING_MAX_RETRIES", "2")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def make_provider(handler: Callable[[httpx.Request], httpx.Response]) -> OllamaEmbeddingProvider:
    """Build a provider whose HTTP calls go to our fake handler. No waiting between retries."""
    return OllamaEmbeddingProvider(transport=httpx.MockTransport(handler), retry_base_delay=0)


def ok_response(request: httpx.Request) -> httpx.Response:
    """Fake Ollama: each vector is the text length repeated DIMENSIONS times."""
    texts = json.loads(request.content)["input"]
    return httpx.Response(200, json={"embeddings": [[float(len(t))] * DIMENSIONS for t in texts]})


def test_documents_are_sent_in_batches_of_32() -> None:
    batch_sizes: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        batch_sizes.append(len(json.loads(request.content)["input"]))
        return ok_response(request)

    vectors = asyncio.run(make_provider(handler).embed_documents(["x"] * 70))

    assert batch_sizes == [32, 32, 6]
    assert len(vectors) == 70


def test_vectors_keep_the_order_of_the_texts() -> None:
    vectors = asyncio.run(make_provider(ok_response).embed_documents(["a", "bb", "ccc"]))

    assert [v[0] for v in vectors] == [1.0, 2.0, 3.0]


def test_embed_query_returns_one_vector() -> None:
    vector = asyncio.run(make_provider(ok_response).embed_query("hello"))

    assert vector == [5.0] * DIMENSIONS


def test_empty_text_is_refused_before_any_request() -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return ok_response(request)

    with pytest.raises(EmbeddingError) as error:
        asyncio.run(make_provider(handler).embed_documents(["fine", "   "]))

    assert error.value.status_code == 400
    assert calls == []


def test_wrong_vector_size_is_detected() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"embeddings": [[0.1, 0.2, 0.3]]})  # 3 instead of 4

    with pytest.raises(EmbeddingError) as error:
        asyncio.run(make_provider(handler).embed_documents(["hello"]))

    assert "dimensions" in str(error.value)


def test_missing_model_gives_a_helpful_message_and_no_retry() -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(404, json={"error": "model not found"})

    with pytest.raises(EmbeddingError) as error:
        asyncio.run(make_provider(handler).embed_documents(["hello"]))

    assert "ollama pull" in str(error.value)
    assert len(calls) == 1


def test_temporary_server_error_is_retried_then_succeeds() -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        if len(calls) == 1:
            return httpx.Response(503)
        return ok_response(request)

    vectors = asyncio.run(make_provider(handler).embed_documents(["hello"]))

    assert len(calls) == 2
    assert len(vectors) == 1


def test_gives_up_after_max_retries() -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(503)

    with pytest.raises(EmbeddingError) as error:
        asyncio.run(make_provider(handler).embed_documents(["hello"]))

    assert error.value.status_code == 502
    assert len(calls) == 3  # 1 first attempt + 2 retries (EMBEDDING_MAX_RETRIES=2)


def test_unreachable_server_becomes_a_503_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    with pytest.raises(EmbeddingError) as error:
        asyncio.run(make_provider(handler).embed_documents(["hello"]))

    assert error.value.status_code == 503


def test_factory_returns_the_ollama_provider_by_default() -> None:
    assert isinstance(get_embedding_provider(), OllamaEmbeddingProvider)


def test_factory_rejects_an_unknown_provider() -> None:
    with pytest.raises(EmbeddingError) as error:
        get_embedding_provider("nope")

    assert error.value.status_code == 400