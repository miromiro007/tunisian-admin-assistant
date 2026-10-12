"""Measure the REAL size of a RAG prompt in Ollama and compare it with our estimate.

Usage (from the project root, venv activated):
    python scripts/context_budget_demo.py "Quel est le taux ... ?" --top-k 20
"""
import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import connect  # noqa: E402
from app.embeddings.factory import get_embedding_provider  # noqa: E402
from app.llm.factory import get_provider  # noqa: E402
from app.rag.context import build_context, estimate_tokens  # noqa: E402
from app.search import search_chunks  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Real prompt size vs estimate")
    parser.add_argument("question")
    parser.add_argument("--top-k", type=int, default=20, help="large on purpose: a stress test")
    args = parser.parse_args()

    vector = await get_embedding_provider().embed_query(args.question)
    with connect() as connection:
        hits = search_chunks(connection, vector, chunk_config="article_1500", top_k=args.top_k)

    # Huge budget: we want to see the whole prompt, not a cut one.
    built = build_context(hits, max_tokens=1_000_000)
    system = "Reply with the single word OK."
    user = f"Sources:\n{built.text}\n\nQuestion: {args.question}"
    estimated = estimate_tokens(system) + estimate_tokens(user)

    provider = get_provider("ollama")
    completion = await provider._complete(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0,
    )
    print(f"sources: {len(built.sources)}   prompt characters: {len(system) + len(user)}")
    print(f"estimated tokens: {estimated}")
    print(f"REAL tokens read by Ollama: {completion.prompt_tokens}")
    print(f"model reply: {completion.text.strip()[:60]}")


if __name__ == "__main__":
    asyncio.run(main())