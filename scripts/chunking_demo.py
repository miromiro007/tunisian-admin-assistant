"""Step 3 experiment: see chunking in action on a small fake legal text.

Run from the project root (venv activated):
    python scripts/chunking_demo.py
"""
import sys
from pathlib import Path

# Make "app" importable when running this script directly from the project root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ingestion.chunking import chunk_by_article, chunk_fixed_size  # noqa: E402

# A short fake text shaped like a legal code (NOT real law, only for the demo).
SAMPLE_TEXT = """CODE DU TRAVAIL - EXTRAIT DE DEMONSTRATION

Article premier
Le present code regit les rapports de travail entre employeurs et salaries.

Article 2
Tout salarie a droit a un conge annuel paye. La duree du conge est fixee par la loi.

Article 3 bis
Le contrat de travail peut etre conclu pour une duree determinee ou indeterminee.
"""


def show(title: str, chunks: list) -> None:
    print(f"\n=== {title}: {len(chunks)} chunks ===")
    for i, c in enumerate(chunks, start=1):
        preview = c.text.replace("\n", " ")[:70]
        print(f"[{i}] article={c.article!s:<8} len={len(c.text):<4} | {preview}")


def main() -> None:
    show("By article", chunk_by_article(SAMPLE_TEXT, "demo.pdf", page=1))
    show(
        "Fixed size (size=120, overlap=30)",
        chunk_fixed_size(SAMPLE_TEXT, "demo.pdf", page=1, chunk_size=120, overlap=30),
    )

    # Show the overlap concretely
    fixed = chunk_fixed_size(SAMPLE_TEXT, "demo.pdf", chunk_size=120, overlap=30)
    print("\nEnd of chunk 1  :", repr(fixed[0].text[-30:]))
    print("Start of chunk 2:", repr(fixed[1].text[:30]))


if __name__ == "__main__":
    main()