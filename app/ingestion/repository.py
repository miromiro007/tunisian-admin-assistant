"""Database access for ingestion. The only place that writes SQL for documents and chunks."""
from dataclasses import dataclass
from typing import Protocol

import psycopg


@dataclass(frozen=True)
class StoredDocument:
    """What we need to know about a document that is already in the database."""

    id: int
    content_hash: str


@dataclass(frozen=True)
class DocumentInfo:
    """A document to store (one row of the `documents` table)."""

    name: str
    title: str
    language: str
    content_hash: str
    page_count: int
    source_url: str | None = None


@dataclass(frozen=True)
class ChunkRow:
    """A chunk ready to store (one row of the `chunks` table)."""

    chunk_index: int
    page: int | None
    article: str | None
    language: str
    content: str
    embedding: list[float]


class ChunkRepository(Protocol):
    """What the pipeline needs from a database. Tests plug an in-memory fake here."""

    def find_document(self, name: str) -> StoredDocument | None: ...

    def count_chunks(self, document_id: int, chunk_config: str) -> int: ...

    def save_chunks(
        self,
        document: DocumentInfo,
        chunk_config: str,
        rows: list[ChunkRow],
        replace_all_configs: bool,
    ) -> None: ...


def to_vector_literal(vector: list[float]) -> str:
    """Format a vector the way pgvector reads it as text: '[0.1,0.2,0.3]'.

    8 significant digits is enough: pgvector stores 32-bit floats.
    """
    return "[" + ",".join(f"{x:.8g}" for x in vector) + "]"


class PostgresChunkRepository:
    """ChunkRepository implemented with PostgreSQL + pgvector."""

    def __init__(self, connection: psycopg.Connection) -> None:
        self._conn = connection

    def find_document(self, name: str) -> StoredDocument | None:
        row = self._conn.execute(
            "SELECT id, content_hash FROM documents WHERE name = %s", (name,)
        ).fetchone()
        return StoredDocument(id=row[0], content_hash=row[1]) if row else None

    def count_chunks(self, document_id: int, chunk_config: str) -> int:
        row = self._conn.execute(
            "SELECT count(*) FROM chunks WHERE document_id = %s AND chunk_config = %s",
            (document_id, chunk_config),
        ).fetchone()
        return int(row[0]) if row else 0

    def save_chunks(
        self,
        document: DocumentInfo,
        chunk_config: str,
        rows: list[ChunkRow],
        replace_all_configs: bool,
    ) -> None:
        """Replace the chunks of one (document, chunk_config) in ONE transaction.

        Either everything is saved, or nothing changes: a crash in the middle can never
        leave half a document in the database. That is what makes re-running safe.
        """
        with self._conn.transaction():
            doc_id = self._conn.execute(
                """
                INSERT INTO documents (name, title, language, source_url, content_hash, page_count)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (name) DO UPDATE SET
                    title        = EXCLUDED.title,
                    language     = EXCLUDED.language,
                    source_url   = COALESCE(EXCLUDED.source_url, documents.source_url),
                    content_hash = EXCLUDED.content_hash,
                    page_count   = EXCLUDED.page_count,
                    ingested_at  = now()
                RETURNING id
                """,
                (
                    document.name, document.title, document.language,
                    document.source_url, document.content_hash, document.page_count,
                ),
            ).fetchone()[0]

            if replace_all_configs:
                # The PDF itself changed: chunks of every configuration are out of date.
                self._conn.execute("DELETE FROM chunks WHERE document_id = %s", (doc_id,))
            else:
                self._conn.execute(
                    "DELETE FROM chunks WHERE document_id = %s AND chunk_config = %s",
                    (doc_id, chunk_config),
                )

            with self._conn.cursor() as cursor:
                cursor.executemany(
                    """
                    INSERT INTO chunks
                        (document_id, chunk_config, chunk_index, page, article,
                         language, content, embedding)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s::vector)
                    """,
                    [
                        (
                            doc_id, chunk_config, row.chunk_index, row.page, row.article,
                            row.language, row.content, to_vector_literal(row.embedding),
                        )
                        for row in rows
                    ],
                )