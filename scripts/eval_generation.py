"""Evaluate the generator: refusals, expected facts, citation support and validity.

Usage (from the project root, venv activated, Docker stack up):
    python scripts/eval_generation.py
    python scripts/eval_generation.py --min-score 0.5 --top-k 5 --show-answers
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
from app.evaluation import first_hit_rank  # noqa: E402
from app.llm.factory import get_provider  # noqa: E402
from app.rag.generation import generate_answer  # noqa: E402
from app.search import search_chunks  # noqa: E402

IN_SCOPE_FILE = ROOT / "eval" / "questions.json"
OUT_OF_SCOPE_FILE = ROOT / "eval" / "out_of_scope.json"
RESULTS_FILE = ROOT / "eval" / "results_generation.md"

sys.stdout.reconfigure(encoding="utf-8")


def contains_keywords(text: str, keywords: list[str]) -> bool:
    """True if the text contains ALL keywords ('a|b' = a or b). Reuses the retrieval eval rule."""
    return first_hit_rank([text], keywords) is not None


def mark(value: bool) -> str:
    return "yes" if value else "no"


async def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the RAG generator")
    parser.add_argument("--provider", default="ollama", choices=["ollama", "groq"])
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--min-score", type=float, default=None)
    parser.add_argument("--show-answers", action="store_true", help="print each in-scope answer")
    args = parser.parse_args()

    in_scope = json.loads(IN_SCOPE_FILE.read_text(encoding="utf-8"))
    out_of_scope = json.loads(OUT_OF_SCOPE_FILE.read_text(encoding="utf-8"))
    embedder = get_embedding_provider()
    llm = get_provider(args.provider)

    lines = [
        f"provider={llm.name}/{llm.model} top_k={args.top_k} min_score={args.min_score}",
        "",
        "## In-scope questions",
        "",
        "| id | best score | right chunk retrieved | refused | facts in answer | cited source supports | invalid citations |",
        "|---|---:|---|---|---|---|---:|",
    ]
    refused_in = answered_facts = supported_count = invalid_total = uncited = 0
    out_rows: list[str] = []
    refused_out = 0

    with connect() as connection:
        for item in in_scope:
            vector = await embedder.embed_query(item["question"])
            hits = search_chunks(
                connection, vector, chunk_config="article_1500", top_k=args.top_k
            )
            result = await generate_answer(llm, item["question"], hits, min_score=args.min_score)

            keywords = item["keywords"]
            retrieved = first_hit_rank([h.content for h in hits], keywords) is not None
            facts = (not result.refused) and contains_keywords(result.answer, keywords)
            cited_texts = [s.hit.content for s in result.sources if s.number in result.cited_numbers]
            supported = any(contains_keywords(text, keywords) for text in cited_texts)

            refused_in += result.refused
            answered_facts += facts
            supported_count += supported
            invalid_total += len(result.invalid_citations)
            uncited += (not result.refused) and not result.cited_numbers
            best = hits[0].score if hits else 0.0
            lines.append(
                f"| {item['id']} | {best:.3f} | {mark(retrieved)} | {mark(result.refused)} | "
                f"{mark(facts)} | {mark(supported)} | {len(result.invalid_citations)} |"
            )
            reason = f" ({result.refusal_reason})" if result.refused else ""
            print(f"{item['id']}: score={best:.3f} refused={result.refused}{reason} facts={facts} supported={supported}")
            if args.show_answers:
                print(f"    keywords: {item['keywords']}")
                print(f"    answer: {' '.join(result.answer.split())[:300]}")

        for item in out_of_scope:
            vector = await embedder.embed_query(item["question"])
            hits = search_chunks(
                connection, vector, chunk_config="article_1500", top_k=args.top_k
            )
            result = await generate_answer(llm, item["question"], hits, min_score=args.min_score)
            refused_out += result.refused
            best = hits[0].score if hits else 0.0
            reason = result.refusal_reason or "answered"
            out_rows.append(f"| {item['id']} | {best:.3f} | {reason} |")
            print(f"{item['id']}: score={best:.3f} -> {reason}")
            if not result.refused:
                print(f"    ANSWER: {result.answer[:150]}")

    total_in, total_out = len(in_scope), len(out_of_scope)
    lines += [
        "",
        "## Out-of-scope questions (the right behavior is to refuse)",
        "",
        "| id | best score | outcome |",
        "|---|---:|---|",
        *out_rows,
        "",
        "## Summary",
        "",
        f"- in-scope refused (over-refusal): {refused_in}/{total_in}",
        f"- in-scope answers containing the expected facts: {answered_facts}/{total_in}",
        f"- in-scope answers whose cited source supports the facts: {supported_count}/{total_in}",
        f"- answers with no citation at all: {uncited}",
        f"- invalid (fake) citations: {invalid_total}",
        f"- out-of-scope refused (correct): {refused_out}/{total_out}",
    ]
    report = "\n".join(lines) + "\n"
    RESULTS_FILE.write_text(report, encoding="utf-8")
    print("\n" + report)
    print(f"Saved to {RESULTS_FILE}")


if __name__ == "__main__":
    asyncio.run(main())