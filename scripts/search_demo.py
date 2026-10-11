"""Ask a question and print the closest chunks.

Usage (from the project root):
    python scripts/search_demo.py "Quelles sont les cotisations CNSS ?"
    python scripts/search_demo.py "..." --config fixed_500 --top-k 3 --language fr
"""
import argparse
import asyncio
import sys
from pathlib import Path

# Make "import app" work when the script is started as `python scripts/search_demo.py`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import connect  # noqa: E402
from app.embeddings.factory import get_embedding_provider  # noqa: E402
from app.search import search_chunks  # noqa: E402

# Windows consoles often use cp1252: force UTF-8 so Arabic text does not crash the script.
sys.stdout.reconfigure(encoding="utf-8")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Semantic search demo")
    parser.add_argument("question")
    parser.add_argument("--config", default="article_1500")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--language", choices=["fr", "ar"], default=None)
    args = parser.parse_args()

    # 1) The question becomes a vector, with the SAME model used for the chunks.
    provider = get_embedding_provider()
    query_vector = await provider.embed_query(args.question)

    # 2) PostgreSQL finds the closest chunks.
    with connect() as connection:
        hits = search_chunks(
            connection,
            query_vector,
            chunk_config=args.config,
            top_k=args.top_k,
            language=args.language,
        )

    print(f"\nQuestion: {args.question}  [config={args.config}]\n")
    for rank, hit in enumerate(hits, start=1):
        snippet = " ".join(hit.content.split())[:300]
        print(f"#{rank}  score={hit.score:.3f}  {hit.document}  p.{hit.page}  {hit.article or '-'}")
        print(f"    {snippet}\n")


if __name__ == "__main__":
    asyncio.run(main())