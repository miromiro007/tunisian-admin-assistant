"""Tests for POST /search: the embedder and the database are replaced by fakes."""
import psycopg
import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.search import SearchHit

client = TestClient(main.app)


class FakeEmbedder:
    async def embed_query(self, text: str) -> list[float]:
        return [0.1] * 1024


def make_hit() -> SearchHit:
    return SearchHit(
        score=0.71, document="cnss.pdf", page=36, article="41",
        language="fr", chunk_config="article_1500", content="Art. 41 ...",
    )


@pytest.fixture(autouse=True)
def fake_embedder(monkeypatch):
    monkeypatch.setattr(main, "get_embedding_provider", lambda: FakeEmbedder())


@pytest.fixture
def calls(monkeypatch) -> list[tuple]:
    """Replace the database call and remember how it was called."""
    recorded: list[tuple] = []

    def fake_search(vector, chunk_config, top_k, language):
        recorded.append((len(vector), chunk_config, top_k, language))
        return [make_hit()]

    monkeypatch.setattr(main, "_search_database", fake_search)
    return recorded


def test_search_returns_the_hits_as_json(calls):
    response = client.post("/search", json={"question": "taux de cotisation"})
    assert response.status_code == 200
    body = response.json()
    assert body["chunk_config"] == "article_1500"
    assert body["hits"][0]["document"] == "cnss.pdf"
    assert body["hits"][0]["page"] == 36
    assert body["hits"][0]["article"] == "41"


def test_defaults_and_options_reach_the_database_layer(calls):
    client.post("/search", json={"question": "taux de cotisation"})
    client.post(
        "/search",
        json={"question": "taux", "top_k": 3, "chunk_config": "fixed_500", "language": "ar"},
    )
    assert calls == [(1024, "article_1500", 5, None), (1024, "fixed_500", 3, "ar")]


@pytest.mark.parametrize(
    "body",
    [
        {"question": ""},
        {"question": "ab"},
        {"question": "taux de cotisation", "top_k": 0},
        {"question": "taux de cotisation", "top_k": 21},
        {"question": "taux de cotisation", "chunk_config": "nope"},
        {"question": "taux de cotisation", "language": "en"},
    ],
)
def test_invalid_requests_are_rejected_with_422(calls, body):
    assert client.post("/search", json=body).status_code == 422
    assert calls == []  # nothing was embedded or searched


def test_database_down_gives_503(monkeypatch):
    def broken(*args):
        raise psycopg.OperationalError("connection refused")

    monkeypatch.setattr(main, "_search_database", broken)
    response = client.post("/search", json={"question": "taux de cotisation"})
    assert response.status_code == 503