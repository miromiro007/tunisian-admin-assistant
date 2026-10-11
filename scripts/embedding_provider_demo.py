"""Step 8 experiment: use the embedding provider with the real Ollama (needs bge-m3 pulled).

Run from the project root (venv activated):
    python scripts/embedding_provider_demo.py
"""
import asyncio
import logging
import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.embeddings.factory import get_embedding_provider  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

PASSAGES: list[str] = [
    "The employee has the right to paid annual leave.",
    "Le salarié a droit à un congé annuel payé.",
    "للعامل الحق في عطلة سنوية مدفوعة الأجر.",
    "Le préavis de licenciement dure un mois.",
    "Pour préparer le couscous, il faut de la semoule et des légumes.",
]
QUESTION: str = "Combien de jours de congé annuel ai-je droit ?"


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    return dot / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))


async def main() -> None:
    provider = get_embedding_provider()
    print(f"Provider: {provider.name} | model: {provider.model} | dimensions: {provider.dimensions}")

    start = time.perf_counter()
    passage_vectors = await provider.embed_documents(PASSAGES)
    elapsed_ms = int((time.perf_counter() - start) * 1000)
    print(f"{len(passage_vectors)} passages embedded in {elapsed_ms} ms\n")

    question_vector = await provider.embed_query(QUESTION)
    print(f"Question: {QUESTION}\n")

    # A first, tiny search: rank the passages by similarity to the question.
    ranked = sorted(
        zip(PASSAGES, passage_vectors),
        key=lambda pair: cosine(question_vector, pair[1]),
        reverse=True,
    )
    for passage, vector in ranked:
        print(f"{cosine(question_vector, vector):.3f}  {passage}")


if __name__ == "__main__":
    asyncio.run(main()) 