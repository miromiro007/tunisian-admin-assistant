-- Runs ONCE, the first time the database volume is created (empty data folder).
-- Docker executes every .sql file in /docker-entrypoint-initdb.d in alphabetical order.

-- Enable the pgvector extension (adds the "vector" type and the <=> operator).
CREATE EXTENSION IF NOT EXISTS vector;

-- One row per source PDF.
CREATE TABLE IF NOT EXISTS documents (
    id            SERIAL PRIMARY KEY,
    name          TEXT        NOT NULL UNIQUE,   -- file name, e.g. code_du_travail_ar_2004.pdf
    title         TEXT,                          -- human-readable title
    language      TEXT        NOT NULL CHECK (language IN ('fr', 'ar')),
    source_url    TEXT,                          -- where the PDF came from (for the README)
    content_hash  TEXT        NOT NULL,          -- SHA-256 of the file: detects changes on re-run
    page_count    INTEGER,
    ingested_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- One row per chunk of text, with its embedding.
CREATE TABLE IF NOT EXISTS chunks (
    id            BIGSERIAL PRIMARY KEY,
    document_id   INTEGER     NOT NULL REFERENCES documents (id) ON DELETE CASCADE,
    chunk_config  TEXT        NOT NULL,          -- chunking strategy label, e.g. article_1500
    chunk_index   INTEGER     NOT NULL,          -- order of the chunk inside the document
    page          INTEGER,                       -- page where the chunk starts (for citations)
    article       TEXT,                          -- article label, e.g. "12" or "premier"
    language      TEXT        NOT NULL CHECK (language IN ('fr', 'ar')),
    content       TEXT        NOT NULL,          -- the chunk text
    embedding     vector(1024) NOT NULL,         -- bge-m3 gives 1024 numbers
    -- Re-running ingestion must never create duplicates:
    UNIQUE (document_id, chunk_config, chunk_index)
);

-- Speeds up filtering by document or by chunking configuration.
CREATE INDEX IF NOT EXISTS idx_chunks_document_config ON chunks (document_id, chunk_config);

-- NOTE: we do NOT create the vector (HNSW) index yet.
-- First we search without an index (exact search), then we add HNSW and compare.