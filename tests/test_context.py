"""Tests for the context builder (no database, no LLM)."""
from app.rag.context import build_context, estimate_tokens
from app.search import SearchHit


def _hit(content: str, article: str = "1", page: int = 1, law_title: str | None = None,
         chunk_id: int = 1) -> SearchHit:
    return SearchHit(
        score=0.5, document="doc_fr.pdf", page=page, article=article, language="fr",
        chunk_config="article_1500", content=content, id=chunk_id, law_title=law_title,
    )


def test_sources_are_numbered_in_order_with_label() -> None:
    hits = [_hit("texte un", "15", 195, "LOI 2004-71", 1), _hit("texte deux", "3", 320, None, 2)]
    built = build_context(hits)
    assert [s.number for s in built.sources] == [1, 2]
    assert "[1] LOI 2004-71 | Art. 15 | p.195\ntexte un" in built.text
    assert "[2] doc_fr.pdf | Art. 3 | p.320\ntexte deux" in built.text
    assert built.dropped == 0

def test_lowest_ranked_hits_are_dropped_when_budget_is_full() -> None:
    hits = [_hit("mot " * 175, chunk_id=i) for i in (1, 2, 3)]
    # Budget sized from the builder's own estimate, so the test survives a change of ratio:
    # room for exactly two chunks (plus separators), not for three.
    one_chunk = build_context([hits[0]]).estimated_tokens
    built = build_context(hits, max_tokens=2 * one_chunk + 10)
    assert [s.hit.id for s in built.sources] == [1, 2]
    assert built.dropped == 1

def test_first_chunk_is_kept_but_cut_if_alone_it_exceeds_the_budget() -> None:
    built = build_context([_hit("x" * 10000)], max_tokens=100)
    assert len(built.sources) == 1
    assert built.estimated_tokens <= 100


def test_empty_hits_give_empty_context() -> None:
    built = build_context([])
    assert built.text == "" and built.sources == [] and built.dropped == 0


def test_arabic_costs_more_tokens_than_french_for_the_same_length() -> None:
    assert estimate_tokens("ا" * 100) > estimate_tokens("a" * 100)