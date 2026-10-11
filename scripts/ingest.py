"""Step 9: ingest the PDFs of data/raw into PostgreSQL + pgvector.

Examples (from the project root, venv activated):
    python scripts/ingest.py                              # article_1500 on every PDF in data/raw
    python scripts/ingest.py --config fixed_500 fixed_1000
    python scripts/ingest.py --config all                 # every chunking configuration
    python scripts/ingest.py --force                      # re-embed even if already stored
"""
import argparse
import asyncio
import logging
import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings  # noqa: E402
from app.db import connect  # noqa: E402
from app.embeddings.errors import EmbeddingError  # noqa: E402
from app.embeddings.factory import get_embedding_provider  # noqa: E402
from app.ingestion.configs import CONFIGS, DEFAULT_CONFIG  # noqa: E402
from app.ingestion.pipeline import IngestResult, ingest_document  # noqa: E402
from app.ingestion.repository import PostgresChunkRepository  # noqa: E402

RAW_DIR = Path("data/raw")
logger = logging.getLogger("ingest")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest PDFs into PostgreSQL + pgvector.")
    parser.add_argument(
        "--config",
        nargs="+",
        default=[DEFAULT_CONFIG],
        choices=[*CONFIGS, "all"],
        help="chunking configuration(s) to use (default: %(default)s)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="re-embed and replace the chunks even if the file is already stored",
    )
    return parser.parse_args()


def print_summary(results: list[IngestResult]) -> None:
    print("\n" + "=" * 78)
    print(f"{'document':<42}{'config':<14}{'status':<10}{'chunks':>7}{'sec':>7}")
    print("-" * 78)
    for r in results:
        print(f"{r.document[:41]:<42}{r.chunk_config:<14}{r.status:<10}{r.chunk_count:>7}{r.seconds:>7.1f}")
    print("=" * 78)


async def run(config_names: list[str], force: bool) -> int:
    pdf_paths = sorted(RAW_DIR.glob("*.pdf"))
    if not pdf_paths:
        logger.error("No PDF found in %s. Run this from the project root.", RAW_DIR.resolve())
        return 1

    provider = get_embedding_provider()
    results: list[IngestResult] = []
    try:
        with connect() as connection:
            repository = PostgresChunkRepository(connection)
            for path in pdf_paths:
                for config_name in config_names:
                    results.append(
                        await ingest_document(path, CONFIGS[config_name], repository, provider, force)
                    )
    except EmbeddingError as error:
        logger.error("Embedding failed (the database was not modified for this file): %s", error)
        return 1
    except psycopg.OperationalError as error:
        logger.error(
            "Cannot use the database: %s. Is it running (docker compose up -d db) "
            "and is DATABASE_URL correct in .env?", error,
        )
        return 1

    print_summary(results)
    return 0


def main() -> None:
    args = parse_args()
    config_names = list(CONFIGS) if "all" in args.config else args.config

    logging.basicConfig(
        level=get_settings().log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)  # one line per request is too noisy here
    sys.exit(asyncio.run(run(config_names, args.force)))


if __name__ == "__main__":
    main()