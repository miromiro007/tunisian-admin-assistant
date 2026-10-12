-- Full-text search column, computed automatically from content + language.
-- Arabic chunks use the 'arabic' config, everything else 'french'.
ALTER TABLE chunks ADD COLUMN IF NOT EXISTS ts tsvector
    GENERATED ALWAYS AS (
        to_tsvector(
            CASE WHEN language = 'ar' THEN 'arabic'::regconfig ELSE 'french'::regconfig END,
            content
        )
    ) STORED;

-- Inverted index: makes "ts @@ query" fast.
CREATE INDEX IF NOT EXISTS idx_chunks_ts ON chunks USING gin (ts);