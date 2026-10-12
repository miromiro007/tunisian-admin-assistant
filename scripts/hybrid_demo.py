"""Show where the right chunk ranks in vector, keyword and hybrid search.

Usage: python scripts/hybrid_demo.py "question" --find "6.75" --language fr
"""
import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import connect  # noqa: E402
from app.embeddings.factory import get_embedding_provider  # noqa: E402
from app.evaluation import first_hit_rank  # noqa: E402
from app.keyword_search import keyword_search  # noqa: E402
from app.search import hybrid_search, search_chunks  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Vector vs keyword vs hybrid")
    parser.add_argument("question")
    parser.add_argument("--find", required=True, help="text the right chunk must contain")
    parser.add_argument("--config", default="article_1500")
    parser.add_argument("--language", choices=["fr", "ar"], default=None)
    parser.add_argument("--top-k", type=int, default=20)
    args = parser.parse_args()

    vector = await get_embedding_provider().embed_query(args.question)
    with connect() as connection:
        vector_hits = search_chunks(connection, vector, chunk_config=args.config,
                                    top_k=args.top_k, language=args.language)
        keyword_hits = keyword_search(connection, args.question, chunk_config=args.config,
                                      top_k=args.top_k, language=args.language)
        hybrid_hits = hybrid_search(connection, args.question, vector, chunk_config=args.config,
                                    top_k=args.top_k, language=args.language)

    for name, hits in (("vector", vector_hits), ("keyword", keyword_hits), ("hybrid", hybrid_hits)):
        rank = first_hit_rank([h.content for h in hits], [args.find])
        print(f"{name:8s} rank of the right chunk: {rank if rank else 'not in top ' + str(args.top_k)}")


if __name__ == "__main__":
    asyncio.run(main())