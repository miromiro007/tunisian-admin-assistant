"""Chunking configurations. Each one has a name that is stored with its chunks in the database."""
from dataclasses import dataclass


@dataclass(frozen=True)
class ChunkConfig:
    name: str       # label stored in chunks.chunk_config
    strategy: str   # "article" (one chunk per article) or "fixed" (sliding window)
    max_chars: int  # maximum chunk size in characters
    overlap: int    # characters repeated between two consecutive chunks


CONFIGS: dict[str, ChunkConfig] = {
    config.name: config
    for config in (
        ChunkConfig("article_1500", "article", 1500, 150),
        ChunkConfig("fixed_500", "fixed", 500, 50),
        ChunkConfig("fixed_1000", "fixed", 1000, 100),
    )
}

DEFAULT_CONFIG: str = "article_1500"