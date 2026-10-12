"""Show the keyword search results for a question.

Usage: python scripts/keyword_demo.py "Quel est le taux ... ?" --top-k 10
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import connect  # noqa: E402
from app.keyword_search import keyword_search  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Keyword search demo")
    parser.add_argument("question")
    parser.add_argument("--config", default="article_1500")
    parser.add_argument("--top-k", type=int, default=10)
    args = parser.parse_args()

    with connect() as connection:
        hits = keyword_search(connection, args.question, chunk_config=args.config, top_k=args.top_k)

    print(f"\nQuestion: {args.question}  [config={args.config}]\n")
    for rank, hit in enumerate(hits, start=1):
        snippet = " ".join(hit.content.split())[:200]
        print(f"#{rank}  rank={hit.score:.3f}  p.{hit.page}  {hit.article or '-'}  (id {hit.id})")
        print(f"    {snippet}\n")


if __name__ == "__main__":
    main()