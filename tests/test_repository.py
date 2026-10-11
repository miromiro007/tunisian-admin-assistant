"""Integration tests of the SQL, against a REAL PostgreSQL + pgvector. Optional.

They are skipped unless TEST_DATABASE_URL is set. They EMPTY the tables, so the database
name MUST end with "_test": they refuse to run on any other database (never your dev data).

Setup (cmd, once, from the project root):
    docker compose exec db createdb -U tunisian tunisian_admin_test
    set TEST_DATABASE_URL=postgresql://tunisian:YOUR_PASSWORD@localhost:5433/tunisian_admin_test
    python -m pytest tests/test_repository.py -v
"""
import os
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest

from app.ingestion.repository import ChunkRow, DocumentInfo, PostgresChunkRepository

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "")

pytestmark = pytest.mark.skipif(not TEST_DATABASE_URL, reason="TEST_DATABASE_URL is not set")

SCHEMA = Path(__file__).resolve().parent.parent / "db" / "init" / "001_schema.sql"


@pytest.fixture
def connection() -> Iterator[psycopg.Connection]:
    assert TEST_DATABASE_URL.rsplit("/", 1)[-1].endswith("_test"), (
        "Refusing to run: the database name must end with '_test'."
    )
    with psycopg.connect(TEST_DATABASE_URL, autocommit=True) as conn:
        conn.execute(SCHEMA.read_text(encoding="utf-8"))
        conn.execute("TRUNCATE chunks, documents RESTART IDENTITY CASCADE")
        yield conn


def document(content_hash: str = "hash-1") -> DocumentInfo:
    return DocumentInfo("loi_fr_2020.pdf", "loi fr 2020", "fr", content_hash, 10)


def rows(count: int) -> list[ChunkRow]:
    vector = [0.0] * 1023 + [1.0]  # 1024 numbers, like bge-m3
    return [ChunkRow(i, 1, str(i), "fr", f"texte {i}", vector) for i in range(count)]


def test_saved_document_and_chunks_can_be_found(connection: psycopg.Connection) -> None:
    repository = PostgresChunkRepository(connection)

    repository.save_chunks(document(), "article_1500", rows(3), replace_all_configs=False)

    stored = repository.find_document("loi_fr_2020.pdf")
    assert stored is not None and stored.content_hash == "hash-1"
    assert repository.count_chunks(stored.id, "article_1500") == 3
    assert repository.find_document("unknown.pdf") is None


def test_saving_the_same_configuration_twice_creates_no_duplicates(connection: psycopg.Connection) -> None:
    repository = PostgresChunkRepository(connection)

    repository.save_chunks(document(), "article_1500", rows(3), replace_all_configs=False)
    repository.save_chunks(document(), "article_1500", rows(3), replace_all_configs=False)

    stored = repository.find_document("loi_fr_2020.pdf")
    assert repository.count_chunks(stored.id, "article_1500") == 3


def test_replace_all_configs_removes_the_other_configurations(connection: psycopg.Connection) -> None:
    repository = PostgresChunkRepository(connection)
    repository.save_chunks(document(), "article_1500", rows(3), replace_all_configs=False)
    repository.save_chunks(document(), "fixed_500", rows(5), replace_all_configs=False)

    repository.save_chunks(document("hash-2"), "article_1500", rows(2), replace_all_configs=True)

    stored = repository.find_document("loi_fr_2020.pdf")
    assert stored.content_hash == "hash-2"
    assert repository.count_chunks(stored.id, "article_1500") == 2
    assert repository.count_chunks(stored.id, "fixed_500") == 0


def test_a_failing_insert_rolls_everything_back(connection: psycopg.Connection) -> None:
    repository = PostgresChunkRepository(connection)
    repository.save_chunks(document(), "article_1500", rows(3), replace_all_configs=False)
    bad_rows = rows(2) + [ChunkRow(2, 1, "x", "xx", "texte", [0.0] * 1024)]  # language "xx" is refused

    with pytest.raises(psycopg.errors.CheckViolation):
        repository.save_chunks(document(), "article_1500", bad_rows, replace_all_configs=False)

    stored = repository.find_document("loi_fr_2020.pdf")
    assert repository.count_chunks(stored.id, "article_1500") == 3  # the old chunks are still there