"""Keyword (full-text) search over the stored chunks, using PostgreSQL tsvector + GIN."""
import re
from dataclasses import dataclass

import psycopg

ARABIC_LETTERS = re.compile(r"[\u0600-\u06FF]")


@dataclass(frozen=True)
class KeywordHit:
    """One keyword result. `score` is ts_rank_cd (not comparable with cosine scores)."""

    id: int
    score: float
    document: str
    page: int | None
    article: str | None
    language: str
    law_title: str | None
    content: str


def query_config(question: str) -> str:
    """Text-search config of the QUESTION: 'arabic' if it contains Arabic letters."""
    return "arabic" if ARABIC_LETTERS.search(question) else "french"


# plainto_tsquery joins words with AND (too strict for a full question).
# We cast it to text, replace '&' by '|', and cast back: any matching word counts.
KEYWORD_SQL = """
WITH q AS (
    SELECT replace(plainto_tsquery(%s::regconfig, %s)::text, '&', '|')::tsquery AS query
)
SELECT c.id, ts_rank_cd(c.ts, q.query) AS score,
       d.name, c.page, c.article, c.language, c.law_title, c.content
FROM chunks c
JOIN documents d ON d.id = c.document_id, q
WHERE c.chunk_config = %s
  AND (%s::text IS NULL OR c.language = %s::text)
  AND c.ts @@ q.query
ORDER BY score DESC
LIMIT %s
"""


def keyword_search(
    connection: psycopg.Connection,
    question: str,
    *,
    chunk_config: str,
    top_k: int = 5,
    language: str | None = None,
) -> list[KeywordHit]:
    """Return the top_k chunks that share the most words with the question."""
    rows = connection.execute(
        KEYWORD_SQL,
        (query_config(question), question, chunk_config, language, language, top_k),
    ).fetchall()
    return [
        KeywordHit(
            id=row[0], score=float(row[1]), document=row[2], page=row[3],
            article=row[4], language=row[5], law_title=row[6], content=row[7],
        )
        for row in rows
    ]