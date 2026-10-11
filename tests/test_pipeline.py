"""Tests for the ingestion pipeline, with an in-memory fake database and a fake embedder.

No PostgreSQL, no Ollama and no GPU are needed.

Run from the project root (venv activated):
    python -m pytest tests -v
"""
import asyncio
from pathlib import Path

import pymupdf
import pytest

from app.embeddings.base import EmbeddingProvider
from app.embeddings.errors import EmbeddingError
from app.ingestion.configs import CONFIGS
from app.ingestion.pdf_loader import PageText
from app.ingestion.pipeline import build_text, ingest_document, make_chunks, page_index_at
from app.ingestion.repository import ChunkRow, DocumentInfo, StoredDocument

ARTICLE = CONFIGS["article_1500"]
FIXED = CONFIGS["fixed_500"]


# ---------- fakes ----------

class FakeProvider(EmbeddingProvider):
    """Returns tiny vectors and counts how many texts it was asked to embed."""

    name = "fake"
    model = "fake"
    dimensions = 3

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.embedded_texts = 0

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if self.fail:
            raise EmbeddingError("ollama is not reachable.", 503)
        self.embedded_texts += len(texts)
        return [[1.0, 0.0, 0.0] for _ in texts]

    async def embed_query(self, text: str) -> list[float]:
        return [1.0, 0.0, 0.0]


class FakeRepository:
    """Same behaviour as PostgresChunkRepository, kept in memory."""

    def __init__(self) -> None:
        self.documents: dict[str, tuple[int, str]] = {}  # name -> (id, hash)
        self.chunks: dict[tuple[int, str], list[ChunkRow]] = {}  # (doc id, config) -> rows

    def find_document(self, name: str) -> StoredDocument | None:
        found = self.documents.get(name)
        return StoredDocument(id=found[0], content_hash=found[1]) if found else None

    def count_chunks(self, document_id: int, chunk_config: str) -> int:
        return len(self.chunks.get((document_id, chunk_config), []))

    def save_chunks(
        self, document: DocumentInfo, chunk_config: str, rows: list[ChunkRow], replace_all_configs: bool
    ) -> None:
        doc_id = self.documents.get(document.name, (len(self.documents) + 1, ""))[0]
        self.documents[document.name] = (doc_id, document.content_hash)
        if replace_all_configs:
            for key in [k for k in self.chunks if k[0] == doc_id]:
                del self.chunks[key]
        self.chunks[(doc_id, chunk_config)] = rows


def make_pdf(path: Path, text: str) -> Path:
    """Create a small real PDF with the given text on one page."""
    document = pymupdf.open()
    document.new_page().insert_text((72, 72), text)
    document.save(path)
    document.close()
    return path


# ---------- page numbers ----------

def pages(*texts: str, first_page: int = 5) -> list[PageText]:
    return [PageText("loi_fr.pdf", first_page + i, text, "fr") for i, text in enumerate(texts)]


def test_page_index_finds_the_page_of_a_position() -> None:
    text, starts = build_text(pages("aaaa", "bbbb", "cccc"))  # starts: 0, 5, 10

    assert starts == [0, 5, 10]
    assert text == "aaaa\nbbbb\ncccc"
    assert [page_index_at(starts, p) for p in (0, 4, 5, 9, 10, 13)] == [0, 0, 1, 1, 2, 2]


def test_each_chunk_gets_the_page_where_it_starts() -> None:
    chunks = make_chunks(pages("Article 1\nabc", "Article 2\ndef"), ARTICLE)

    assert [(c.article, c.page) for c in chunks] == [("1", 5), ("2", 6)]


def test_article_spanning_two_pages_gets_its_first_page() -> None:
    chunks = make_chunks(pages("Article 1\nabc", "suite de l'article 1\nArticle 2\ndef"), ARTICLE)

    assert [(c.article, c.page) for c in chunks] == [("1", 5), ("2", 6)]


def test_page_numbers_follow_the_pdf_even_if_pages_were_skipped() -> None:
    skipped = [PageText("loi_fr.pdf", 3, "Article 1\nabc", "fr"), PageText("loi_fr.pdf", 9, "Article 2\ndef", "fr")]

    assert [c.page for c in make_chunks(skipped, ARTICLE)] == [3, 9]


# ---------- re-runnable ingestion ----------

def ingest(path: Path, config, repository: FakeRepository, provider: FakeProvider, force: bool = False):
    return asyncio.run(ingest_document(path, config, repository, provider, force))


def test_first_run_ingests_the_document(tmp_path: Path) -> None:
    pdf = make_pdf(tmp_path / "loi_fr_2020.pdf", "Article 1\nPremier texte.\nArticle 2\nSecond texte.")
    repository, provider = FakeRepository(), FakeProvider()

    result = ingest(pdf, ARTICLE, repository, provider)

    assert result.status == "ingested"
    assert result.chunk_count == 2
    assert provider.embedded_texts == 2


def test_second_run_skips_and_does_not_embed_again(tmp_path: Path) -> None:
    pdf = make_pdf(tmp_path / "loi_fr_2020.pdf", "Article 1\nPremier texte.")
    repository, provider = FakeRepository(), FakeProvider()
    ingest(pdf, ARTICLE, repository, provider)

    second = ingest(pdf, ARTICLE, repository, provider)

    assert second.status == "skipped"
    assert provider.embedded_texts == 1  # only the first run embedded something


def test_force_replaces_the_chunks_without_duplicates(tmp_path: Path) -> None:
    pdf = make_pdf(tmp_path / "loi_fr_2020.pdf", "Article 1\nPremier texte.\nArticle 2\nSecond texte.")
    repository, provider = FakeRepository(), FakeProvider()
    ingest(pdf, ARTICLE, repository, provider)

    forced = ingest(pdf, ARTICLE, repository, provider, force=True)

    assert forced.status == "ingested"
    assert repository.count_chunks(1, ARTICLE.name) == 2  # still 2, not 4


def test_another_configuration_is_ingested_next_to_the_first(tmp_path: Path) -> None:
    pdf = make_pdf(tmp_path / "loi_fr_2020.pdf", "Article 1\nPremier texte.")
    repository, provider = FakeRepository(), FakeProvider()
    ingest(pdf, ARTICLE, repository, provider)

    result = ingest(pdf, FIXED, repository, provider)

    assert result.status == "ingested"
    assert repository.count_chunks(1, ARTICLE.name) > 0
    assert repository.count_chunks(1, FIXED.name) > 0


def test_changed_file_replaces_the_chunks_of_every_configuration(tmp_path: Path) -> None:
    pdf = tmp_path / "loi_fr_2020.pdf"
    repository, provider = FakeRepository(), FakeProvider()
    make_pdf(pdf, "Article 1\nVersion un.")
    ingest(pdf, ARTICLE, repository, provider)
    ingest(pdf, FIXED, repository, provider)

    make_pdf(pdf, "Article 1\nVersion deux, completement differente.")  # the file changes
    ingest(pdf, ARTICLE, repository, provider)

    assert repository.count_chunks(1, ARTICLE.name) > 0
    assert repository.count_chunks(1, FIXED.name) == 0  # stale chunks are gone


def test_embedding_failure_leaves_the_database_untouched(tmp_path: Path) -> None:
    pdf = make_pdf(tmp_path / "loi_fr_2020.pdf", "Article 1\nPremier texte.")
    repository = FakeRepository()

    with pytest.raises(EmbeddingError):
        ingest(pdf, ARTICLE, repository, FakeProvider(fail=True))

    assert repository.documents == {}
    assert repository.chunks == {}


def test_pdf_without_text_is_refused(tmp_path: Path) -> None:
    blank = tmp_path / "vide_fr_2020.pdf"
    document = pymupdf.open()
    document.new_page()  # a page with no text, like a scan
    document.save(blank)
    document.close()

    with pytest.raises(ValueError):
        ingest(blank, ARTICLE, FakeRepository(), FakeProvider())