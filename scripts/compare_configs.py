"""Compare the chunking configurations on a fixed set of questions.

eval/questions.json lists, for each question, words that MUST appear in the right chunk.
A search "hits at rank r" when the r-th result contains all of them.

Usage (from the project root):
    python scripts/compare_configs.py
    python scripts/compare_configs.py --top-k 5
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
from app.ingestion.configs import CONFIGS  # noqa: E402
from app.search import search_chunks  # noqa: E402

QUESTIONS_FILE = ROOT / "eval" / "questions.json"
RESULTS_FILE = ROOT / "eval" / "results.md"

# Windows consoles often use cp1252: force UTF-8 so Arabic text cannot crash the script.
sys.stdout.reconfigure(encoding="utf-8")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Compare chunking configurations")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    questions = json.loads(QUESTIONS_FILE.read_text(encoding="utf-8"))

    # Each question is embedded ONCE and reused for every configuration.
    provider = get_embedding_provider()
    vectors = [await provider.embed_query(q["question"]) for q in questions]

    ranks: dict[str, list[int | None]] = {}
    with connect() as connection:
        for config in CONFIGS:
            ranks[config] = []
            for question, vector in zip(questions, vectors):
                hits = search_chunks(
                    connection,
                    vector,
                    chunk_config=config,
                    top_k=args.top_k,
                    language=question["language"],
                )
                ranks[config].append(first_hit_rank([h.content for h in hits], question["keywords"]))

    report = build_report(questions, ranks)
    RESULTS_FILE.write_text(report, encoding="utf-8")
    print(report)
    print(f"Saved to {RESULTS_FILE}")


if __name__ == "__main__":
    asyncio.run(main())