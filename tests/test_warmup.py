"""Tests for the warm-up: it calls both models, a failure never propagates, startup launches it."""
import asyncio

from fastapi.testclient import TestClient

import app.main as main
import app.warmup as warmup
from app.llm.base import Completion


class FakeEmbedder:
    def __init__(self) -> None:
        self.calls = 0

    async def embed_query(self, text: str) -> list[float]:
        self.calls += 1
        return [0.0]


class FakeLLM:
    def __init__(self) -> None:
        self.calls = 0

    async def complete_messages(self, messages, temperature) -> Completion:
        self.calls += 1
        return Completion("OK", 10, 1)


def test_warm_up_calls_both_models(monkeypatch) -> None:
    embedder, llm = FakeEmbedder(), FakeLLM()
    monkeypatch.setattr(warmup, "get_embedding_provider", lambda: embedder)
    monkeypatch.setattr(warmup, "get_provider", lambda name: llm)
    asyncio.run(warmup.warm_up_models())
    assert embedder.calls == 1 and llm.calls == 1


def test_warm_up_failure_does_not_propagate(monkeypatch) -> None:
    class Broken:
        async def embed_query(self, text: str) -> list[float]:
            raise RuntimeError("ollama is down")

    monkeypatch.setattr(warmup, "get_embedding_provider", lambda: Broken())
    asyncio.run(warmup.warm_up_models())  # must not raise


def test_startup_launches_warm_up(monkeypatch) -> None:
    calls = 0

    async def fake_warm_up() -> None:
        nonlocal calls
        calls += 1

    monkeypatch.setattr(main.settings, "rag_warmup", True)
    monkeypatch.setattr(main, "warm_up_models", fake_warm_up)

    # The `with` block runs the lifespan (startup/shutdown); a bare TestClient(...) would not.
    # Startup fails (NameError) if main.py stops importing asyncio.
    with TestClient(main.app) as client:
        assert client.get("/health").status_code == 200
        # Checked inside the block: shutdown cancels the warm-up task.
        assert calls == 1