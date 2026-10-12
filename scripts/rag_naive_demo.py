"""Naive RAG demo: observe hallucination, grounding and the score baseline.

Usage (from the project root, venv activated):
    python scripts/rag_naive_demo.py
"""
import asyncio
import sys
from pathlib import Path

# Make "import app" work when started as `python scripts/rag_naive_demo.py`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import connect  # noqa: E402
from app.embeddings.factory import get_embedding_provider  # noqa: E402
from app.llm.base import LLMProvider  # noqa: E402
from app.llm.factory import get_provider  # noqa: E402
from app.search import SearchHit, search_chunks  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

# ---- Questions (edit them if you want to try others) ----
IN_SCOPE_QUESTION = "Quel est le taux de cotisation patronale à la CNSS ?"
OUT_OF_SCOPE_QUESTION = "Quel est le taux de TVA en Tunisie ?"

TOP_K = 5
MAX_CHARS_PER_CHUNK = 1500  # keeps the prompt small enough for the model


# ---- Prompts defined locally (the real grounded prompt comes in Step 6) ----
NO_CONTEXT_SYSTEM = (
    "You are an assistant for Tunisian administration. "
    "Answer briefly in the same language as the question."
)

GROUNDED_SYSTEM = (
    "You are an assistant for Tunisian administration. "
    "Answer briefly in the same language as the question, "
    "using ONLY the numbered sources provided. "
    "Cite the source numbers like [1]. "
    "If the sources do not contain the answer, say you do not know."
)


async def retrieve(question: str) -> list[SearchHit]:
    """Embed the question, then find the closest chunks in PostgreSQL."""
    embedder = get_embedding_provider()
    query_vector = await embedder.embed_query(question)
    with connect() as connection:
        return search_chunks(
            connection,
            query_vector,
            chunk_config="article_1500",
            top_k=TOP_K,
            language=None,
        )


def build_context(hits: list[SearchHit]) -> str:
    """Format the chunks as numbered sources: [1] ..., [2] ..."""
    blocks = []
    for number, hit in enumerate(hits, start=1):
        text = " ".join(hit.content.split())[:MAX_CHARS_PER_CHUNK]
        header = f"[{number}] {hit.document}, p.{hit.page}, {hit.article or '-'}"
        blocks.append(f"{header}\n{text}")
    return "\n\n".join(blocks)


async def call_llm(provider: LLMProvider, system: str, user: str) -> str:
    """One LLM call, temperature 0 so the result is repeatable."""
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    completion = await provider._complete(messages, temperature=0)
    return completion.text.strip()


def print_scores(hits: list[SearchHit]) -> None:
    print("  Retrieval scores:")
    for rank, hit in enumerate(hits, start=1):
        print(f"    #{rank} score={hit.score:.3f}  {hit.document} p.{hit.page} {hit.article or '-'}")


async def main() -> None:
    provider = get_provider("ollama")
    print(f"LLM: {provider.name} / {provider.model}")

    # ---------- CASE A: in-scope question, NO context ----------
    print(f"\n=== CASE A: no context ===\nQ: {IN_SCOPE_QUESTION}")
    answer = await call_llm(provider, NO_CONTEXT_SYSTEM, IN_SCOPE_QUESTION)
    print(f"A: {answer}")

    # ---------- CASE B: same question, WITH retrieved context ----------
    print(f"\n=== CASE B: with context ===\nQ: {IN_SCOPE_QUESTION}")
    hits = await retrieve(IN_SCOPE_QUESTION)
    print_scores(hits)
    user_prompt = f"Sources:\n{build_context(hits)}\n\nQuestion: {IN_SCOPE_QUESTION}"
    answer = await call_llm(provider, GROUNDED_SYSTEM, user_prompt)
    print(f"A: {answer}")

    # ---------- CASE C: out-of-scope question, WITH retrieved context ----------
    print(f"\n=== CASE C: out of scope ===\nQ: {OUT_OF_SCOPE_QUESTION}")
    hits = await retrieve(OUT_OF_SCOPE_QUESTION)
    print_scores(hits)
    user_prompt = f"Sources:\n{build_context(hits)}\n\nQuestion: {OUT_OF_SCOPE_QUESTION}"
    answer = await call_llm(provider, GROUNDED_SYSTEM, user_prompt)
    print(f"A: {answer}")


if __name__ == "__main__":
    asyncio.run(main())