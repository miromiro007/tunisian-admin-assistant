"""Search over the stored chunks: vector search, and hybrid (vector + keyword) search."""
from dataclasses import dataclass

import psycopg

from app.keyword_search import KeywordHit, keyword_search


@dataclass(frozen=True)
class SearchHit:
    """One result of a search."""

    score: float  # vector: cosine similarity (~0.3 = unrelated). hybrid: RRF score.
    document: str
    page: int | None
    article: str | None
    language: str
    chunk_config: str
    content: str
    id: int | None = None          # chunk id in the database (needed to merge and to cite)
    law_title: str | None = None   # law/section title from the page header


# <=> is pgvector's cosine DISTANCE (0 = identical), so similarity = 1 - distance.
# ORDER BY distance ascending = most similar first.
# "(%s::text IS NULL OR c.language = %s::text)" makes the language filter optional.
SEARCH_SQL = """
SELECT 1 - (c.embedding <=> %s::vector) AS score,
       d.name, c.page, c.article, c.language, c.chunk_config, c.content,
       c.id, c.law_title
FROM chunks c
JOIN documents d ON d.id = c.document_id
WHERE c.chunk_config = %s
  AND (%s::text IS NULL OR c.language = %s::text)
ORDER BY c.embedding <=> %s::vector
LIMIT %s
"""

RRF_K = 60            # standard RRF constant
CANDIDATES = 20       # how many results we take from EACH list before merging


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
            id=row[7],
            law_title=row[8],
        )
        for row in rows
    ]


def reciprocal_rank_fusion(
    rankings: list[list[int]], k: int = RRF_K
) -> list[tuple[int, float]]:
    """Merge several ranked lists of ids into one.

    Each id gets 1 / (k + rank) from every list that contains it (rank starts at 1).
    Returns (id, score) sorted by score descending; ties are broken by id (repeatable).
    Pure function: no database, easy to test.
    """
    scores: dict[int, float] = {}
    for ranking in rankings:
        for rank, item_id in enumerate(ranking, start=1):
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda item: (-item[1], item[0]))


def _hit_from_keyword(hit: KeywordHit, chunk_config: str, score: float) -> SearchHit:
    """A chunk found only by the keyword search, converted to a SearchHit."""
    return SearchHit(
        score=score,
        document=hit.document,
        page=hit.page,
        article=hit.article,
        language=hit.language,
        chunk_config=chunk_config,
        content=hit.content,
        id=hit.id,
        law_title=hit.law_title,
    )


def hybrid_search(
    connection: psycopg.Connection,
    question: str,
    query_vector: list[float],
    *,
    chunk_config: str,
    top_k: int = 5,
    language: str | None = None,
    candidates: int = CANDIDATES,
) -> list[SearchHit]:
    """Vector search + keyword search, merged with Reciprocal Rank Fusion.

    The returned `score` is the RRF score (a small number, only meaningful for ordering).
    """
    vector_hits = search_chunks(
        connection, query_vector, chunk_config=chunk_config, top_k=candidates, language=language
    )
    keyword_hits = keyword_search(
        connection, question, chunk_config=chunk_config, top_k=candidates, language=language
    )

    by_id: dict[int, SearchHit] = {}
    for hit in vector_hits:
        if hit.id is not None:
            by_id[hit.id] = hit
    for keyword_hit in keyword_hits:
        by_id.setdefault(keyword_hit.id, _hit_from_keyword(keyword_hit, chunk_config, 0.0))

    fused = reciprocal_rank_fusion(
        [
            [hit.id for hit in vector_hits if hit.id is not None],
            [hit.id for hit in keyword_hits],
        ]
    )
    results: list[SearchHit] = []
    for chunk_id, rrf_score in fused[:top_k]:
        from dataclasses import replace  # local import keeps the top of the file short

        results.append(replace(by_id[chunk_id], score=rrf_score))
    return results