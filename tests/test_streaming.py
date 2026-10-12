"""Tests for streaming: provider fallback, generation events and POST /ask/stream."""
import asyncio
import json

import psycopg
import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.llm.base import Completion, LLMProvider, StreamChunk
from app.llm.errors import LLMError
from app.rag.generation import StreamEvent, generate_answer_stream
from app.rag.prompts import NO_ANSWER_MARKER
from app.search import SearchHit


class FakeEmbedder:
    async def embed_query(self, text: str) -> list[float]:
        return [0.0, 0.0, 0.0]


class FakeStreamLLM:
    """Streams the given pieces. If fail_after is set, raises an LLMError at that piece."""

    name = "fake"
    model = "fake-1"

    def __init__(self, pieces: list[str], fail_after: int | None = None) -> None:
        self.pieces = pieces
        self.fail_after = fail_after
        self.calls = 0

    async def stream_messages(self, messages, temperature):
        self.calls += 1
        for index, piece in enumerate(self.pieces):
            if self.fail_after is not None and index == self.fail_after:
                raise LLMError("ollama is not reachable.", 503)
            yield StreamChunk(piece)
        yield StreamChunk("", done=True, prompt_tokens=50, completion_tokens=10)


def _hit(chunk_id: int, score: float = 0.8) -> SearchHit:
    return SearchHit(
        score=score, document="doc_fr.pdf", page=10 + chunk_id, article=str(chunk_id),
        language="fr", chunk_config="article_1500", content=f"contenu de l'article {chunk_id}",
        id=chunk_id, law_title="LOI TEST",
    )


def _events(llm, question: str, hits: list[SearchHit], **kwargs) -> list[StreamEvent]:
    async def collect() -> list[StreamEvent]:
        return [e async for e in generate_answer_stream(llm, question, hits, **kwargs)]

    return asyncio.run(collect())


# ---------- provider fallback ----------

def test_default_stream_gives_the_whole_text_then_done() -> None:
    class MinimalProvider(LLMProvider):
        name = "minimal"

        @property
        def model(self) -> str:
            return "m"

        async def _complete(self, messages, temperature, json_schema=None) -> Completion:
            return Completion("bonjour", 5, 2)

    async def drain() -> list[StreamChunk]:
        return [c async for c in MinimalProvider().stream_messages([], 0.0)]

    chunks = asyncio.run(drain())
    assert chunks[0].text == "bonjour"
    assert chunks[-1].done and chunks[-1].completion_tokens == 2


# ---------- generation events ----------

def test_tokens_are_streamed_and_final_has_citations() -> None:
    llm = FakeStreamLLM(["Le taux ", "est de 6,75 % ", "[2]."])
    events = _events(llm, "Quel taux ?", [_hit(1), _hit(2)])
    kinds = [e.kind for e in events]
    assert kinds[0] == "sources" and kinds[-1] == "final"
    assert "".join(e.text for e in events if e.kind == "token") == "Le taux est de 6,75 % [2]."
    assert events[-1].answer.cited_numbers == [2]


def test_refusal_marker_is_not_streamed() -> None:
    events = _events(FakeStreamLLM([NO_ANSWER_MARKER, " [1][2]."]), "Quel taux ?", [_hit(1)])
    assert [e.kind for e in events if e.kind == "token"] == []
    assert events[-1].answer.refused and events[-1].answer.refusal_reason == "model_declined"


def test_marker_split_across_chunks_is_still_caught() -> None:
    events = _events(FakeStreamLLM(["NO_", "ANSWER", " [1]."]), "Quel taux ?", [_hit(1)])
    assert not any(e.kind == "token" for e in events)
    assert events[-1].answer.refusal_reason == "model_declined"


def test_low_score_gives_only_a_final_refusal() -> None:
    llm = FakeStreamLLM(["ne doit pas être appelé"])
    events = _events(llm, "Quel taux ?", [_hit(1, score=0.3)], min_score=0.6)
    assert [e.kind for e in events] == ["final"]
    assert events[0].answer.refusal_reason == "below_threshold" and llm.calls == 0


# ---------- the route ----------

@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(main, "get_embedding_provider", lambda: FakeEmbedder())
    return TestClient(main.app)


def _setup(monkeypatch: pytest.MonkeyPatch, hits: list[SearchHit], llm: FakeStreamLLM) -> None:
    monkeypatch.setattr(main, "_search_database", lambda *args: hits)
    monkeypatch.setattr(main, "get_provider", lambda name: llm)


def _parse_sse(body: str) -> list[tuple[str, dict]]:
    events = []
    for block in body.strip().split("\n\n"):
        lines = block.split("\n")
        name = lines[0].removeprefix("event: ")
        events.append((name, json.loads(lines[1].removeprefix("data: "))))
    return events


def test_route_streams_sources_tokens_then_done(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    _setup(monkeypatch, [_hit(1), _hit(2)], FakeStreamLLM(["Le taux est de ", "6,75 % [2]."]))
    response = client.post("/ask/stream", json={"question": "Quel est le taux ?"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = _parse_sse(response.text)
    names = [name for name, _ in events]
    assert names[0] == "sources" and names[-1] == "done"
    assert all(name == "token" for name in names[1:-1]) and len(names) >= 3
    done = events[-1][1]
    assert done["refused"] is False and [c["number"] for c in done["citations"]] == [2]
    assert done["timings"]["first_token_ms"] is not None


def test_route_refusal_has_no_tokens(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    _setup(monkeypatch, [_hit(1)], FakeStreamLLM([NO_ANSWER_MARKER]))
    events = _parse_sse(client.post("/ask/stream", json={"question": "Quel est le taux ?"}).text)
    assert [name for name, _ in events] == ["sources", "done"]
    assert events[-1][1]["refused"] is True and events[-1][1]["refusal_reason"] == "model_declined"


def test_route_database_down_is_503_before_streaming(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken(*args):
        raise psycopg.OperationalError("down")

    monkeypatch.setattr(main, "_search_database", broken)
    assert client.post("/ask/stream", json={"question": "Quel est le taux ?"}).status_code == 503


def test_route_llm_error_during_the_stream_becomes_an_error_event(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _setup(monkeypatch, [_hit(1)], FakeStreamLLM(["Le taux est de ", "6,75 %"], fail_after=1))
    events = _parse_sse(client.post("/ask/stream", json={"question": "Quel est le taux ?"}).text)
    assert events[-1][0] == "error" and events[-1][1]["status"] == 503