"""Tests for the generation service, with a fake LLM (no network, no database)."""
import asyncio

from app.llm.base import Completion
from app.rag.generation import build_messages, detect_language, generate_answer, parse_citations
from app.rag.prompts import NO_ANSWER_MARKER, REFUSAL_AR, REFUSAL_FR
from app.search import SearchHit
from app.rag.prompts import NO_ANSWER_MARKER, REFUSAL_AR, REFUSAL_FR, REMINDER


class FakeProvider:
    """Plays the role of an LLM: returns a fixed text and remembers what it was asked."""

    name = "fake"
    model = "fake-1"

    def __init__(self, text: str) -> None:
        self.text = text
        self.calls = 0
        self.messages: list[dict[str, str]] = []

    async def complete_messages(self, messages: list[dict[str, str]], temperature: float) -> Completion:
        self.calls += 1
        self.messages = messages
        return Completion(self.text, prompt_tokens=100, completion_tokens=20)


def _hit(chunk_id: int, score: float = 0.7) -> SearchHit:
    return SearchHit(
        score=score, document="doc_fr.pdf", page=chunk_id, article=str(chunk_id), language="fr",
        chunk_config="article_1500", content=f"contenu {chunk_id}", id=chunk_id, law_title=None,
    )


def _run(provider: FakeProvider, question: str, hits: list[SearchHit], **kwargs):
    return asyncio.run(generate_answer(provider, question, hits, **kwargs))


def test_valid_and_invalid_citations_are_separated() -> None:
    assert parse_citations("Taux 6,75 % [1][3]. Voir [1] et [9].", 3) == ([1, 3], [9])


def test_answer_with_valid_citations() -> None:
    result = _run(FakeProvider("Le taux est de 6,75 % [2]."), "Quel taux ?", [_hit(1), _hit(2)])
    assert not result.refused
    assert result.cited_numbers == [2] and result.invalid_citations == []
    assert len(result.sources) == 2


def test_fake_citation_is_reported() -> None:
    result = _run(FakeProvider("Réponse [7]."), "Quel taux ?", [_hit(1)])
    assert result.invalid_citations == [7] and result.cited_numbers == []


def test_model_declining_gives_localized_refusal() -> None:
    result = _run(FakeProvider(NO_ANSWER_MARKER), "Quel taux de TVA ?", [_hit(1)])
    assert result.refused and result.refusal_reason == "model_declined"
    assert result.answer == REFUSAL_FR


def test_low_score_refuses_without_calling_the_llm() -> None:
    provider = FakeProvider("ne doit pas être appelé")
    result = _run(provider, "Quel taux ?", [_hit(1, score=0.4)], min_score=0.6)
    assert result.refused and result.refusal_reason == "below_threshold"
    assert provider.calls == 0


def test_no_hits_refuses_without_calling_the_llm() -> None:
    provider = FakeProvider("ne doit pas être appelé")
    result = _run(provider, "Quel taux ?", [])
    assert result.refusal_reason == "no_sources" and provider.calls == 0


def test_arabic_question_uses_arabic_prompt_and_refusal() -> None:
    provider = FakeProvider(NO_ANSWER_MARKER)
    result = _run(provider, "ما هي مدة الإجازة السنوية؟", [_hit(1)])
    assert detect_language("ما هي مدة الإجازة السنوية؟") == "ar"
    assert result.language == "ar" and result.answer == REFUSAL_AR
    assert "المصادر" in provider.messages[1]["content"]


def test_reminder_comes_last_and_does_not_end_with_the_refusal_word() -> None:
    messages = build_messages("Quel taux ?", "[1] source", "fr")
    assert messages[0]["role"] == "system"
    assert messages[1]["content"].endswith(REMINDER["fr"])
    assert not messages[1]["content"].rstrip(". ").endswith(NO_ANSWER_MARKER)

def test_answer_with_only_a_citation_is_rejected() -> None:
    result = _run(FakeProvider("[1]"), "Quel taux ?", [_hit(1)])
    assert result.refused and result.refusal_reason == "empty_answer"
    assert result.cited_numbers == []