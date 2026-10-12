"""Tests for POST /ask with fakes: no network, no database, no LLM."""
import psycopg
import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.llm.base import Completion
from app.llm.errors import LLMError
from app.rag.prompts import NO_ANSWER_MARKER
from app.search import SearchHit


class FakeEmbedder:
    async def embed_query(self, text: str) -> list[float]:
        return [0.0, 0.0, 0.0]


class FakeLLM:
    name = "fake"
    model = "fake-1"

    def __init__(self, text: str) -> None:
        self.text = text
        self.calls = 0

    async def complete_messages(self, messages, temperature) -> Completion:
        self.calls += 1
        return Completion(self.text, prompt_tokens=50, completion_tokens=10)


def _hit(chunk_id: int, score: float = 0.8) -> SearchHit:
    return SearchHit(
        score=score, document="doc_fr.pdf", page=10 + chunk_id, article=str(chunk_id),
        language="fr", chunk_config="article_1500", content=f"contenu de l'article {chunk_id}",
        id=chunk_id, law_title="LOI TEST",
    )


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(main, "get_embedding_provider", lambda: FakeEmbedder())
    return TestClient(main.app)


def _setup(monkeypatch: pytest.MonkeyPatch, hits: list[SearchHit], llm: FakeLLM) -> None:
    monkeypatch.setattr(main, "_search_database", lambda *args: hits)
    monkeypatch.setattr(main, "get_provider", lambda name: llm)


def test_answer_with_citation(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    _setup(monkeypatch, [_hit(1), _hit(2)], FakeLLM("Le taux est de 6,75 % [2]."))
    response = client.post("/ask", json={"question": "Quel est le taux ?"})
    assert response.status_code == 200
    body = response.json()
    assert body["refused"] is False and body["language"] == "fr"
    assert [c["number"] for c in body["citations"]] == [2]
    assert body["citations"][0]["law_title"] == "LOI TEST"
    assert len(body["sources"]) == 2 and body["invalid_citations"] == []
    assert body["timings"]["total_ms"] >= 0 and body["provider"] == "fake"


def test_model_declining_is_a_200_refusal(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    _setup(monkeypatch, [_hit(1)], FakeLLM(NO_ANSWER_MARKER))
    body = client.post("/ask", json={"question": "Quel est le taux de TVA ?"}).json()
    assert body["refused"] is True and body["refusal_reason"] == "model_declined"
    assert body["citations"] == []


def test_low_score_refuses_without_calling_the_llm(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    llm = FakeLLM("ne doit pas être appelé")
    _setup(monkeypatch, [_hit(1, score=0.3)], llm)
    body = client.post("/ask", json={"question": "Question hors sujet"}).json()
    assert body["refusal_reason"] == "below_threshold" and llm.calls == 0
    assert body["best_score"] == 0.3


def test_no_hits_refuses(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    _setup(monkeypatch, [], FakeLLM("x"))
    body = client.post("/ask", json={"question": "Quel est le taux ?"}).json()
    assert body["refusal_reason"] == "no_sources" and body["best_score"] is None


def test_fake_citation_is_reported(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    _setup(monkeypatch, [_hit(1)], FakeLLM("Réponse inventée [9]."))
    body = client.post("/ask", json={"question": "Quel est le taux ?"}).json()
    assert body["invalid_citations"] == [9] and body["citations"] == []


def test_validation_error_is_422(client: TestClient) -> None:
    assert client.post("/ask", json={"question": "ab"}).status_code == 422
    assert client.post("/ask", json={"question": "Quel taux ?", "top_k": 99}).status_code == 422


def test_database_down_is_503(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(*args):
        raise psycopg.OperationalError("down")

    monkeypatch.setattr(main, "_search_database", broken)
    assert client.post("/ask", json={"question": "Quel est le taux ?"}).status_code == 503


def test_llm_error_keeps_its_status(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    class BrokenLLM(FakeLLM):
        async def complete_messages(self, messages, temperature):
            raise LLMError("ollama is not reachable.", 503)

    _setup(monkeypatch, [_hit(1)], BrokenLLM("x"))
    response = client.post("/ask", json={"question": "Quel est le taux ?"})
    assert response.status_code == 503 and "not reachable" in response.json()["detail"]