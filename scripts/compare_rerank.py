"""Compare vector search with and without the cross-encoder reranker, on all questions.

Usage (from the project root, venv activated):
    python scripts/compare_rerank.py
    python scripts/compare_rerank.py --candidates 10 --top-k 5
"""
import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import torch  # noqa: E402
from sentence_transformers import CrossEncoder  # noqa: E402

from app.db import connect  # noqa: E402
from app.embeddings.factory import get_embedding_provider  # noqa: E402
from app.evaluation import build_report, first_hit_rank  # noqa: E402
from app.search import search_chunks  # noqa: E402

QUESTIONS_FILE = ROOT / "eval" / "questions.json"
RESULTS_FILE = ROOT / "eval" / "results_rerank.md"
MODEL_NAME = "BAAI/bge-reranker-v2-m3"

sys.stdout.reconfigure(encoding="utf-8")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Vector vs vector + reranker")
    parser.add_argument("--candidates", type=int, default=10, help="chunks sent to the reranker")
    parser.add_argument("--top-k", type=int, default=5, help="chunks kept at the end")
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = parser.parse_args()

    questions = json.loads(QUESTIONS_FILE.read_text(encoding="utf-8"))
    embedder = get_embedding_provider()
    vectors = [await embedder.embed_query(q["question"]) for q in questions]

    # fp16 halves the memory on the GPU (about 1.2 GB instead of 2.3 GB).
    model_kwargs = {"torch_dtype": torch.float16} if args.device == "cuda" else {}
    model = CrossEncoder(MODEL_NAME, device=args.device, max_length=512, model_kwargs=model_kwargs)
    print(f"device={args.device} candidates={args.candidates} top_k={args.top_k}")

    # Warm-up: the first GPU call is slow (kernel setup) and would distort the timings.
    model.predict([("warm-up", "warm-up")])

    ranks: dict[str, list[int | None]] = {"vector": [], "reranked": []}
    seconds: list[float] = []
    with connect() as connection:
        for question, vector in zip(questions, vectors):
            hits = search_chunks(
                connection, vector, chunk_config="article_1500",
                top_k=args.candidates, language=question["language"],
            )
            # Baseline: the vector order, cut at top_k.
            ranks["vector"].append(
                first_hit_rank([h.content for h in hits[: args.top_k]], question["keywords"])
            )

            started = time.perf_counter()
            scores = model.predict([(question["question"], h.content) for h in hits])
            seconds.append(time.perf_counter() - started)

            reranked = [h for _, h in sorted(zip(scores, hits), key=lambda x: -x[0])]
            ranks["reranked"].append(
                first_hit_rank([h.content for h in reranked[: args.top_k]], question["keywords"])
            )

    report = build_report(questions, ranks)
    RESULTS_FILE.write_text(report, encoding="utf-8")
    print(report)
    print(f"reranking time per question: mean {sum(seconds) / len(seconds):.2f}s, max {max(seconds):.2f}s")
    print(f"Saved to {RESULTS_FILE}")


if __name__ == "__main__":
    asyncio.run(main()) 