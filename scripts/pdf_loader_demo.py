"""Step 6 experiment: load and clean the PDFs, compare before and after.

Run from the project root (venv activated):
    python scripts/pdf_loader_demo.py
"""
import logging
import sys
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ingestion.chunking import ARTICLE_PATTERN  # noqa: E402
from app.ingestion.pdf_loader import load_pdf  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

RAW_DIR = Path("data/raw")


def raw_char_count(path: Path) -> int:
    """Number of characters in the PDF before any cleaning."""
    with pymupdf.open(path) as doc:
        return sum(len(page.get_text("text")) for page in doc)


def main() -> None:
    for path in sorted(RAW_DIR.glob("*.pdf")):
        pages = load_pdf(path)
        clean_chars = sum(len(p.text) for p in pages)
        full_text = "\n".join(p.text for p in pages)
        print("=" * 70)
        print(f"File            : {path.name}")
        print(f"Language        : {pages[0].language}")
        print(f"Non-empty pages : {len(pages)}")
        print(f"Chars before    : {raw_char_count(path)}")
        print(f"Chars after     : {clean_chars}")
        print(f"Article starts  : {len(ARTICLE_PATTERN.findall(full_text))}")
        sample = pages[len(pages) // 2]
        print(f"Sample (page {sample.page}):")
        print(sample.text[:400])


if __name__ == "__main__":
    main()