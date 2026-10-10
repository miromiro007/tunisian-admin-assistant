"""Step 2 experiment: measure cosine similarity between sentences.

Run from the project root (venv activated):
    python scripts/cosine_experiment.py
"""
# --- Imports -------------------------------------------------------------
import math  # math.sqrt for the vector length (norm)
import os

import httpx
from dotenv import load_dotenv

# --- Configuration (same pattern as Step 1) ------------------------------
load_dotenv()
OLLAMA_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11435")
MODEL: str = os.getenv("EMBEDDING_MODEL", "bge-m3")

# --- Test sentences ------------------------------------------------------
# A, B, C share the SAME meaning in 3 languages.
# D is about the SAME topic but a different fact (notice period).
# E is completely unrelated (cooking).
SENTENCES: dict[str, str] = {
    "EN": "The employee has the right to paid annual leave.",
    "FR": "Le salarié a droit à un congé annuel payé.",
    "AR": "للعامل الحق في عطلة سنوية مدفوعة الأجر.",
    "FR-other": "Le préavis de licenciement dure un mois.",
    "FR-cooking": "Pour préparer le couscous, il faut de la semoule et des légumes.",
}


def embed(texts: list[str]) -> list[list[float]]:
    """Return one embedding vector per text (batch call to Ollama)."""
    response = httpx.post(
        f"{OLLAMA_URL}/api/embed",
        json={"model": MODEL, "input": texts},
        timeout=120.0,
    )
    response.raise_for_status()
    return response.json()["embeddings"]


def dot(a: list[float], b: list[float]) -> float:
    """Dot product: multiply each pair of numbers, then add everything up."""
    return sum(x * y for x, y in zip(a, b))


def norm(a: list[float]) -> float:
    """Length of a vector: square root of the sum of its squared numbers."""
    return math.sqrt(sum(x * x for x in a))


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity = dot product divided by the product of the lengths.

    Result is in [-1, 1]. Closer to 1 means more similar in meaning.
    """
    return dot(a, b) / (norm(a) * norm(b))


def main() -> None:
    labels = list(SENTENCES.keys())
    vectors = embed(list(SENTENCES.values()))  # one batch call for all 5 sentences

    # Header row of the table
    print(f"{'':<12}" + "".join(f"{label:<12}" for label in labels))

    # One row per sentence: similarity with every sentence (including itself = 1.0)
    for i, label_i in enumerate(labels):
        row = f"{label_i:<12}"
        for j in range(len(labels)):
            score = cosine_similarity(vectors[i], vectors[j])
            row += f"{score:<12.3f}"
        print(row)

    # Also show the vector length: it tells us if the vectors are already normalized
    print(f"\nNorm of the EN vector: {norm(vectors[0]):.4f}")


if __name__ == "__main__":
    main()