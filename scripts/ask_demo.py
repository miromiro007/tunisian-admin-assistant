"""Ask one question end to end: retrieve, build the prompt, generate, validate citations.

Usage (from the project root, venv activated):
    python scripts/ask_demo.py "Quel est le taux ... ?"
    python scripts/ask_demo.py "..." --top-k 5 --min-score 0.6 --provider ollama
"""
import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import connect  # noqa: E402
from app.embeddings.factory import get_embedding_provider  # noqa: E402
from app.llm.factory import get_provider  # noqa: E402
from app.rag.context import build_context  # noqa: E402
from app.rag.generation import build_messages, detect_language, generate_answer  # noqa: E402
from app.search import search_chunks  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Grounded answer demo")
    parser.add_argument("question")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--min-score", type=float, default=None)
    parser.add_argument("--provider", default="ollama", choices=["ollama", "groq"])
    parser.add_argument("--show-prompt", action="store_true", help="print what the model sees")
    args = parser.parse_args()

    vector = await get_embedding_provider().embed_query(args.question)
    with connect() as connection:
        hits = search_chunks(connection, vector, chunk_config="article_1500", top_k=args.top_k)

    best = f"{hits[0].score:.3f}" if hits else "-"
    print(f"\nQuestion: {args.question}\nbest retrieval score: {best}")
    if args.show_prompt:
        context = build_context(hits)
        user = build_messages(args.question, context.text, detect_language(args.question))[1]["content"]
        print("\nSources shown to the model:")
        for block in context.text.split("\n\n"):
            print("  " + block[:170].replace("\n", " | "))
        print("\nEnd of the prompt:\n" + user[-500:])

    result = await generate_answer(
        get_provider(args.provider), args.question, hits, min_score=args.min_score
    )

    print(f"\nANSWER ({'REFUSED: ' + str(result.refusal_reason) if result.refused else 'ok'}):")
    print(result.answer)
    print(f"\ncited: {result.cited_numbers}   invalid: {result.invalid_citations}")
    for source in result.sources:
        if source.number in result.cited_numbers:
            hit = source.hit
            print(f"  [{source.number}] {hit.law_title or hit.document} | Art. {hit.article} | p.{hit.page}")
    print(f"\ntokens in/out: {result.prompt_tokens}/{result.completion_tokens}   {result.latency_ms} ms")


if __name__ == "__main__":
    asyncio.run(main())