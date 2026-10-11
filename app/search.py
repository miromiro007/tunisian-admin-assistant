"""Semantic search over the stored chunks (exact search with pgvector)."""
from dataclasses import dataclass

import psycopg


@dataclass(frozen=True)
class SearchHit:
    """One result of a search."""

    score: float  # cosine similarity: 1.0 = same direction, ~0.3 = unrelated (bge-m3)
    document: str
    page: int | None
    article: str | None
    language: str
    chunk_config: str
    content: str


# <=> is pgvector's cosine DISTANCE (0 = identical), so similarity = 1 - distance.
# ORDER BY distance ascending = most similar first.
# "(%s::text IS NULL OR c.language = %s::text)" makes the language filter optional.
SEARCH_SQL = """
SELECT 1 - (c.embedding <=> %s::vector) AS score,
       d.name, c.page, c.article, c.language, c.chunk_config, c.content
FROM chunks c
JOIN documents d ON d.id = c.document_id
WHERE c.chunk_config = %s
  AND (%s::text IS NULL OR c.language = %s::text)
ORDER BY c.embedding <=> %s::vector
LIMIT %s
"""


def _vector_literal(vector: list[float]) -> str:
    """Python list -> pgvector text format, e.g. '[0.1,0.2,0.3]'."""
    return "[" + ",".join(f"{x:.8g}" for x in vector) + "]"


def search_chunks(
    connection: psycopg.Connection,
    query_vector: list[float],
    *,
    chunk_config: str,
    top_k: int = 5,
    language: str | None = None,
) -> list[SearchHit]:
    """Return the top_k chunks closest to query_vector, for one chunking config."""
    literal = _vector_literal(query_vector)
    rows = connection.execute(
        SEARCH_SQL, (literal, chunk_config, language, language, literal, top_k)
    ).fetchall()
    return [
        SearchHit(
            score=float(row[0]),
            document=row[1],
            page=row[2],
            article=row[3],
            language=row[4],
            chunk_config=row[5],
            content=row[6],
        )
        for row in rows
    ]