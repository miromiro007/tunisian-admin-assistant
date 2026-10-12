"""Compare search modes (vector, keyword, hybrid) on the labeled questions.

Usage (from the project root, venv activated):
    python scripts/compare_modes.py
    python scripts/compare_modes.py --config article_1500 --top-k 5
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.db import connect  # noqa: E402
from app.embeddings.factory import get_embedding_provider  # noqa: E402
from app.evaluation import build_report, first_hit_rank  # noqa: E402
from app.keyword_search import keyword_search  # noqa: E402
from app.search import hybrid_search, search_chunks  # noqa: E402

QUESTIONS_FILE = ROOT / "eval" / "questions.json"
RESULTS_FILE = ROOT / "eval" / "results_modes.md"

sys.stdout.reconfigure(encoding="utf-8")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Compare vector, keyword and hybrid search")
    parser.add_argument("--config", default="article_1500")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    questions = json.loads(QUESTIONS_FILE.read_text(encoding="utf-8"))
    provider = get_embedding_provider()
    vectors = [await provider.embed_query(q["question"]) for q in questions]

    ranks: dict[str, list[int | None]] = {"vector": [], "keyword": [], "hybrid": []}
    with connect() as connection:
        for question, vector in zip(questions, vectors):
            text, language = question["question"], question["language"]
            results = {
                "vector": search_chunks(
                    connection, vector, chunk_config=args.config,
                    top_k=args.top_k, language=language,
                ),
                "keyword": keyword_search(
                    connection, text, chunk_config=args.config,
                    top_k=args.top_k, language=language,
                ),
                "hybrid": hybrid_search(
                    connection, text, vector, chunk_config=args.config,
                    top_k=args.top_k, language=language,
                ),
            }
            for mode, hits in results.items():
                ranks[mode].append(first_hit_rank([h.content for h in hits], question["keywords"]))

    report = build_report(questions, ranks)
    RESULTS_FILE.write_text(report, encoding="utf-8")
    print(f"config={args.config} top_k={args.top_k}\n")
    print(report)
    print(f"Saved to {RESULTS_FILE}")


if __name__ == "__main__":
    asyncio.run(main())