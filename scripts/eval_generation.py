"""Evaluate the generator on one model, optionally several times.

Usage (from the project root, venv activated, Docker stack up):
    python scripts/eval_generation.py --provider ollama --repeat 2 --min-score 0.5
    python scripts/eval_generation.py --provider groq --repeat 2 --min-score 0.5 --delay 3
    python scripts/eval_generation.py --show-answers
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
from app.llm.errors import LLMError  # noqa: E402
from app.llm.factory import get_provider  # noqa: E402
from app.rag.generation import RagAnswer, generate_answer  # noqa: E402
from app.search import SearchHit, search_chunks  # noqa: E402

IN_SCOPE_FILE = ROOT / "eval" / "questions.json"
OUT_OF_SCOPE_FILE = ROOT / "eval" / "out_of_scope.json"

sys.stdout.reconfigure(encoding="utf-8")


def contains_keywords(text: str, keywords: list[str]) -> bool:
    """True if the text contains ALL keywords ('a|b' = a or b). Reuses the retrieval eval rule."""
    return first_hit_rank([text], keywords) is not None


async def generate_with_retry(llm, question: str, hits: list[SearchHit], args) -> RagAnswer | None:
    """One generation. On a 429 (rate limit) wait and retry; any other failure returns None."""
    for attempt in range(3):
        try:
            result = await generate_answer(llm, question, hits, min_score=args.min_score)
            if args.delay:
                await asyncio.sleep(args.delay)
            return result
        except LLMError as exc:
            if exc.status_code == 429 and attempt < 2:
                print("    rate limit reached, waiting 30 s...")
                await asyncio.sleep(30)
                continue
            print(f"    LLM error {exc.status_code}: {exc}")
            return None
    return None


def outcome_in_scope(result: RagAnswer | None, keywords: list[str]) -> tuple[str, bool]:
    """('error'|'refused'|'fact'|'no-fact', cited source supports the facts)."""
    if result is None:
        return "error", False
    if result.refused:
        return "refused", False
    cited = [s.hit.content for s in result.sources if s.number in result.cited_numbers]
    supported = any(contains_keywords(text, keywords) for text in cited)
    return ("fact" if contains_keywords(result.answer, keywords) else "no-fact"), supported


async def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the RAG generator")
    parser.add_argument("--provider", default="ollama", choices=["ollama", "groq"])
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--min-score", type=float, default=None)
    parser.add_argument("--repeat", type=int, default=1, help="how many times to run everything")
    parser.add_argument("--delay", type=float, default=0.0, help="seconds to wait after each LLM call")
    parser.add_argument("--show-answers", action="store_true", help="print each in-scope answer")
    parser.add_argument("--only", default="", help="comma-separated question ids, for a quick look (does not write the results file)")
    args = parser.parse_args()

    in_scope = json.loads(IN_SCOPE_FILE.read_text(encoding="utf-8"))
    out_of_scope = json.loads(OUT_OF_SCOPE_FILE.read_text(encoding="utf-8"))
    if args.only:
        wanted = set(args.only.split(","))
        in_scope = [q for q in in_scope if q["id"] in wanted]
        out_of_scope = [q for q in out_of_scope if q["id"] in wanted]
    embedder = get_embedding_provider()
    llm = get_provider(args.provider)

    # Retrieval is identical for every run and every model: do it once.
    retrieved: dict[str, list[SearchHit]] = {}
    with connect() as connection:
        for item in [*in_scope, *out_of_scope]:
            vector = await embedder.embed_query(item["question"])
            retrieved[item["id"]] = search_chunks(
                connection, vector, chunk_config="article_1500", top_k=args.top_k
            )

    per_question: dict[str, list[str]] = {item["id"]: [] for item in [*in_scope, *out_of_scope]}
    run_summaries: list[str] = []

    for run in range(1, args.repeat + 1):
        print(f"\n===== run {run}/{args.repeat}: {llm.name}/{llm.model} =====")
        refused_in = facts_count = supported_count = invalid_total = errors = 0
        refused_out = 0

        for item in in_scope:
            hits = retrieved[item["id"]]
            result = await generate_with_retry(llm, item["question"], hits, args)
            outcome, supported = outcome_in_scope(result, item["keywords"])
            per_question[item["id"]].append(outcome)
            refused_in += outcome == "refused"
            facts_count += outcome == "fact"
            supported_count += supported
            errors += outcome == "error"
            invalid_total += len(result.invalid_citations) if result else 0
            reason = f" ({result.refusal_reason})" if result and result.refused else ""
            print(f"{item['id']}: {outcome}{reason} supported={supported}")
            if args.show_answers and result:
                print(f"    keywords: {item['keywords']}")
                print(f"    answer: {' '.join(result.answer.split())[:300]}")

        for item in out_of_scope:
            result = await generate_with_retry(llm, item["question"], retrieved[item["id"]], args)
            outcome = "error" if result is None else ("refused" if result.refused else "ANSWERED")
            per_question[item["id"]].append(outcome)
            refused_out += outcome == "refused"
            errors += outcome == "error"
            print(f"{item['id']}: {outcome}")
            if outcome == "ANSWERED":
                print(f"    ANSWER: {result.answer[:150]}")

        run_summaries.append(
            f"| {run} | {facts_count}/{len(in_scope)} | {supported_count}/{len(in_scope)} | "
            f"{refused_in}/{len(in_scope)} | {refused_out}/{len(out_of_scope)} | "
            f"{invalid_total} | {errors} |"
        )

    unstable = [qid for qid, outcomes in per_question.items() if len(set(outcomes)) > 1]
    lines = [
        f"# Generation evaluation: {llm.name}/{llm.model}",
        "",
        f"top_k={args.top_k} min_score={args.min_score} runs={args.repeat}",
        "",
        "## Per run",
        "",
        "| run | facts in answer | cited source supports | in-scope refused | out-of-scope refused | fake citations | errors |",
        "|---:|---:|---:|---:|---:|---:|---:|",
        *run_summaries,
        "",
        "## Per question (one outcome per run)",
        "",
        "| id | " + " | ".join(f"run {r}" for r in range(1, args.repeat + 1)) + " |",
        "|---|" + "---|" * args.repeat,
        *[f"| {qid} | " + " | ".join(outcomes) + " |" for qid, outcomes in per_question.items()],
        "",
        f"Unstable questions (different outcome between runs): {unstable or 'none'}",
        "",
        "Outcomes: fact = the expected keywords are in the answer; no-fact = answered without them; "
        "refused = the system declined; ANSWERED = an out-of-scope question was answered (bad).",
    ]
    report = "\n".join(lines) + "\n"
    if args.only:
        print("\n(--only: quick look, results file not written)")
        return
    results_file = ROOT / "eval" / f"results_generation_{llm.name}.md"
    results_file.write_text(report, encoding="utf-8")
    print("\n" + report)
    print(f"Saved to {results_file}")


if __name__ == "__main__":
    asyncio.run(main())