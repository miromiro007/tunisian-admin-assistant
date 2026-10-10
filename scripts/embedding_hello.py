"""Step 1 experiment: turn sentences into vectors with bge-m3 through Ollama.

Run from the project root:
    python scripts/embedding_hello.py
"""
import os

import httpx

# Where Ollama listens. From Windows (outside Docker) it is localhost:11434.
OLLAMA_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11435")

# The embedding model we pulled.
MODEL: str = "bge-m3"   

# Same meaning, three languages.
SENTENCES: list[str] = [
    "The employee has the right to paid annual leave.",
    "Le salarié a droit à un congé annuel payé.",
    "للعامل الحق في عطلة سنوية مدفوعة الأجر.",
]


def embed(texts: list[str]) -> list[list[float]]:
    """Send a list of texts to Ollama and return one vector per text."""
    response = httpx.post(
        f"{OLLAMA_URL}/api/embed",              # Ollama's embedding endpoint
        json={"model": MODEL, "input": texts},  # "input" accepts a list (batch)
        timeout=120.0,                          # first call loads the model: can be slow
    )
    response.raise_for_status()                 # like EnsureSuccessStatusCode() in .NET
    return response.json()["embeddings"]        # one vector per text, same order


def main() -> None:
    vectors = embed(SENTENCES)
    print(f"Model: {MODEL}")
    print(f"Number of vectors: {len(vectors)}\n")
    for sentence, vector in zip(SENTENCES, vectors):
        print(f"Text      : {sentence}")
        print(f"Dimensions: {len(vector)}")
        print(f"First 5   : {[round(x, 4) for x in vector[:5]]}\n")


if __name__ == "__main__":
    main()