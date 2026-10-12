-- Law (or section) title of each chunk, taken from the running page header.
-- IF NOT EXISTS: safe to run twice, and safe on a fresh database.
ALTER TABLE chunks ADD COLUMN IF NOT EXISTS law_title TEXT;