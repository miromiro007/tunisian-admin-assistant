"""Compare Ollama and Groq on the same questions.

Run from the project root:  python scripts/compare_models.py
Writes results to data/comparison.csv and data/comparison.md
"""
import asyncio
import csv
from pathlib import Path

from app.llm.errors import LLMError
from app.llm.factory import get_provider

# Mix of languages and difficulty, all about Tunisian administration.
QUESTIONS: list[str] = [
    "How do I create a company in Tunisia?",
    "Comment s'inscrire à la CNSS en tant qu'indépendant ?",
    "كيف أسجل في الضمان الاجتماعي؟",
    "How many days of paid annual leave does a worker get in Tunisia?",
    "Quels documents faut-il pour créer une SARL ?",
    "ما هي مدة فترة التجربة في عقد الشغل؟",
    "What is the minimum capital for a SARL in Tunisia?",
    "What is the capital of France?",  # off-topic control question
]

PROVIDERS = ["ollama", "groq"]
OUTPUT_DIR = Path("data")


async def run_one(provider_name: str, question: str) -> dict:
    """Ask one question; return a result row (errors become a row too)."""
    provider = get_provider(provider_name)
    try:
        r = await provider.chat(question, temperature=0)
    except LLMError as exc:
        return {"provider": provider_name, "model": provider.model, "question": question,
                "prompt_tokens": 0, "completion_tokens": 0, "latency_ms": 0,
                "tokens_per_s": 0.0, "answer": f"ERROR: {exc}"}

    seconds = r.latency_ms / 1000
    return {
        "provider": r.provider,
        "model": r.model,
        "question": question,
        "prompt_tokens": r.prompt_tokens,
        "completion_tokens": r.completion_tokens,
        "latency_ms": r.latency_ms,
        "tokens_per_s": round(r.completion_tokens / seconds, 1) if seconds else 0.0,
        "answer": r.answer.replace("\n", " "),
    }


async def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Warm-up: load Qwen into VRAM so the first real question isn't unfairly slow.
    print("Warm-up...")
    await run_one("ollama", "Hello")

    rows: list[dict] = []
    for question in QUESTIONS:
        for name in PROVIDERS:
            print(f"[{name}] {question[:50]}")
            rows.append(await run_one(name, question))
            if name == "groq":
                await asyncio.sleep(2)  # be gentle with the free-tier rate limit

    # Full results (with answers) for you to read and score.
    fields = list(rows[0].keys())
    with open(OUTPUT_DIR / "comparison.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    # Averages per provider, as a Markdown table for the README.
    lines = ["| Provider | Model | Avg latency (ms) | Avg tokens/s | Avg prompt tok | Avg completion tok |",
             "|---|---|---|---|---|---|"]
    for name in PROVIDERS:
        subset = [r for r in rows if r["provider"] == name and not r["answer"].startswith("ERROR")]
        if not subset:
            continue
        n = len(subset)
        lines.append(
            f"| {name} | {subset[0]['model']} "
            f"| {sum(r['latency_ms'] for r in subset) // n} "
            f"| {sum(r['tokens_per_s'] for r in subset) / n:.1f} "
            f"| {sum(r['prompt_tokens'] for r in subset) // n} "
            f"| {sum(r['completion_tokens'] for r in subset) // n} |"
        )
    table = "\n".join(lines)
    (OUTPUT_DIR / "comparison.md").write_text(table, encoding="utf-8")
    print("\n" + table)


if __name__ == "__main__":
    asyncio.run(main())