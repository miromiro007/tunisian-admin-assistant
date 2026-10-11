"""Tests for the chunking strategies (app/ingestion/chunking.py).

Run from the project root (venv activated):
    python -m pytest tests -v
"""
import pytest

from app.ingestion.chunking import Chunk, chunk_by_article, chunk_fixed_size

SAMPLE = """CODE DU TRAVAIL - EXTRAIT

Article premier
Le present code regit les rapports de travail.

Article 2
Tout salarie a droit a un conge annuel paye.

Article 3 bis
Le contrat peut etre a duree determinee ou indeterminee.
"""


def assert_offsets_are_exact(text: str, chunks: list[Chunk]) -> None:
    """Every chunk must be found exactly where `start` says it is."""
    for chunk in chunks:
        assert text[chunk.start : chunk.start + len(chunk.text)] == chunk.text


def test_one_chunk_per_article_with_its_label() -> None:
    chunks = chunk_by_article(SAMPLE, "demo_fr.pdf")

    assert [c.article for c in chunks] == [None, "premier", "2", "3 bis"]


def test_text_before_the_first_article_has_no_label() -> None:
    chunks = chunk_by_article(SAMPLE, "demo_fr.pdf")

    assert chunks[0].article is None
    assert chunks[0].text.startswith("CODE DU TRAVAIL")


def test_chunk_start_points_to_the_chunk_in_the_original_text() -> None:
    assert_offsets_are_exact(SAMPLE, chunk_by_article(SAMPLE, "demo_fr.pdf"))


def test_arabic_articles_are_detected() -> None:
    text = "الفصل 12\nنص الفصل الأول\nالفصل 13\nنص آخر"

    chunks = chunk_by_article(text, "demo_ar.pdf", language="ar")

    assert [c.article for c in chunks] == ["12", "13"]
    assert all(c.language == "ar" for c in chunks)


def test_long_article_is_split_and_keeps_its_label() -> None:
    long_text = "Article 7\n" + ("mot " * 600)  # about 2400 characters
    chunks = chunk_by_article(long_text, "demo_fr.pdf", max_chars=1000, overlap=100)

    assert len(chunks) > 1
    assert {c.article for c in chunks} == {"7"}
    assert all(len(c.text) <= 1000 for c in chunks)
    assert_offsets_are_exact(long_text, chunks)


def test_text_without_articles_falls_back_to_fixed_size() -> None:
    chunks = chunk_by_article("juste du texte " * 100, "demo_fr.pdf", max_chars=300, overlap=30)

    assert len(chunks) > 1
    assert all(c.article is None for c in chunks)


def test_fixed_size_windows_overlap() -> None:
    chunks = chunk_fixed_size("ABCDEFGHIJKLMNOP", "demo_fr.pdf", chunk_size=10, overlap=3)

    assert [c.text for c in chunks] == ["ABCDEFGHIJ", "HIJKLMNOP"]
    assert [c.start for c in chunks] == [0, 7]


def test_fixed_size_offsets_are_exact_even_with_spaces_around() -> None:
    text = "   " + "abcdefghij " * 40 + "   "
    assert_offsets_are_exact(text, chunk_fixed_size(text, "demo_fr.pdf", chunk_size=50, overlap=10))


def test_overlap_must_be_smaller_than_chunk_size() -> None:
    with pytest.raises(ValueError):
        chunk_fixed_size("abc", "demo_fr.pdf", chunk_size=10, overlap=10)


def test_blank_text_gives_no_chunk() -> None:
    assert chunk_fixed_size("   \n  ", "demo_fr.pdf") == []