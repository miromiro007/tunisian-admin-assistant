-- HNSW = approximate nearest-neighbour index (graph of vectors).
-- vector_cosine_ops: the index uses cosine distance, the same as the <=> operator.
-- m = connections per node, ef_construction = build quality (these are pgvector's defaults).
-- One partial index per chunking config: a search always filters on chunk_config,
-- so each config gets its own small graph and nothing is filtered out after the search.
CREATE INDEX IF NOT EXISTS idx_chunks_hnsw_article_1500
    ON chunks USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)
    WHERE chunk_config = 'article_1500';

CREATE INDEX IF NOT EXISTS idx_chunks_hnsw_fixed_500
    ON chunks USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)
    WHERE chunk_config = 'fixed_500';

CREATE INDEX IF NOT EXISTS idx_chunks_hnsw_fixed_1000
    ON chunks USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)
    WHERE chunk_config = 'fixed_1000';