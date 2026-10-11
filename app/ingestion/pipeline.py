"""Ingestion pipeline: PDF -> clean pages -> chunks -> embeddings -> database.

Re-runnable: running it twice never creates duplicates.
  - same file, same configuration, already stored  -> skipped
  - file changed (different SHA-256 hash)          -> everything for that file is replaced
  - --force                                        -> the chunks of that configuration are replaced
"""
import hashlib
import logging
import time
from bisect import bisect_right
from dataclasses import dataclass, replace
from pathlib import Path

from app.embeddings.base import EmbeddingProvider
from app.ingestion.chunking import Chunk, chunk_by_article, chunk_fixed_size
from app.ingestion.configs import ChunkConfig
from app.ingestion.pdf_loader import PageText, load_pdf
from app.ingestion.repository import ChunkRepository, ChunkRow, DocumentInfo

logger = logging.getLogger(__name__)

# Chunks are embedded in slices of this size so we can log progress.
EMBED_SLICE_SIZE: int = 64


@dataclass(frozen=True)
class IngestResult:
    document: str
    chunk_config: str
    status: str          # "ingested" or "skipped"
    chunk_count: int
    seconds: float


def sha256_file(path: Path) -> str:
    """SHA-256 fingerprint of a file: it changes if and only if the file content changes."""
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):  # 1 MB at a time
            digest.update(block)
    return digest.hexdigest()


def build_text(pages: list[PageText]) -> tuple[str, list[int]]:
    """Join all pages into one text (articles can span pages).

    Also returns the position where each page starts, to find the page of any position later.
    """
    starts: list[int] = []
    position = 0
    for page in pages:
        starts.append(position)
        position += len(page.text) + 1  # +1 for the "\n" between pages
    return "\n".join(page.text for page in pages), starts


def page_index_at(page_starts: list[int], position: int) -> int:
    """Index (in the pages list) of the page that contains the given text position."""
    return bisect_right(page_starts, position) - 1


def make_chunks(pages: list[PageText], config: ChunkConfig) -> list[Chunk]:
    """Cut the pages into chunks following `config`, and give each chunk its page number."""
    if not pages:
        return []
    document, language = pages[0].document, pages[0].language
    text, page_starts = build_text(pages)

    if config.strategy == "article":
        chunks = chunk_by_article(
            text, document, None, language, config.max_chars, config.overlap
        )
    elif config.strategy == "fixed":
        chunks = chunk_fixed_size(
            text, document, None, language, config.max_chars, config.overlap
        )
    else:
        raise ValueError(f"Unknown chunking strategy '{config.strategy}'.")

    return [
        replace(chunk, page=pages[page_index_at(page_starts, chunk.start)].page)
        for chunk in chunks
    ]


async def ingest_document(
    path: Path,
    config: ChunkConfig,
    repository: ChunkRepository,
    provider: EmbeddingProvider,
    force: bool = False,
) -> IngestResult:
    """Ingest one PDF with one chunking configuration."""
    started = time.perf_counter()
    file_hash = sha256_file(path)

    stored = repository.find_document(path.name)
    hash_changed = stored is not None and stored.content_hash != file_hash

    # Cheap check first: nothing to do if this exact file is already stored with this config.
    if stored is not None and not hash_changed and not force:
        existing = repository.count_chunks(stored.id, config.name)
        if existing > 0:
            logger.info("SKIP %s [%s]: already ingested (%d chunks)", path.name, config.name, existing)
            return IngestResult(path.name, config.name, "skipped", existing, time.perf_counter() - started)

    if hash_changed:
        logger.warning(
            "%s changed since the last run: chunks of ALL configurations will be replaced. "
            "Re-run the other configurations too.", path.name,
        )

    pages = load_pdf(path)
    chunks = make_chunks(pages, config)
    if not chunks:
        raise ValueError(f"No chunk produced for {path.name}. Is the PDF empty or a scan?")
    sizes = [len(chunk.text) for chunk in chunks]
    logger.info(
        "%s [%s]: %d pages -> %d chunks (min %d, max %d chars)",
        path.name, config.name, len(pages), len(chunks), min(sizes), max(sizes),
    )

    # Embed everything BEFORE touching the database: if Ollama fails, nothing is modified.
    vectors: list[list[float]] = []
    for offset in range(0, len(chunks), EMBED_SLICE_SIZE):
        piece = chunks[offset : offset + EMBED_SLICE_SIZE]
        vectors.extend(await provider.embed_documents([chunk.text for chunk in piece]))
        logger.info("%s [%s]: embedded %d/%d", path.name, config.name, len(vectors), len(chunks))

    rows = [
        ChunkRow(
            chunk_index=index,
            page=chunk.page,
            article=chunk.article,
            language=chunk.language,
            content=chunk.text,
            embedding=vector,
        )
        for index, (chunk, vector) in enumerate(zip(chunks, vectors))
    ]
    document = DocumentInfo(
        name=path.name,
        title=path.stem.replace("_", " "),
        language=pages[0].language,
        content_hash=file_hash,
        page_count=pages[-1].page,
    )
    repository.save_chunks(document, config.name, rows, replace_all_configs=hash_changed)

    elapsed = time.perf_counter() - started
    logger.info("DONE %s [%s]: %d chunks saved in %.1fs", path.name, config.name, len(rows), elapsed)
    return IngestResult(path.name, config.name, "ingested", len(rows), elapsed)