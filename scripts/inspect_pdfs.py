"""Step 5: inspect every PDF in data/raw to see if its text can be extracted.

Run from the project root (venv activated):
    python scripts/inspect_pdfs.py
"""
# --- Imports -------------------------------------------------------------
import re
import sys
from pathlib import Path

import fitz  # PyMuPDF: reads PDFs (the package is "pymupdf", the import name is "fitz")

# Make "app" importable when running this script from the project root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ingestion.chunking import ARTICLE_PATTERN  # noqa: E402  (our Step 3 regex)

# Windows consoles often use a legacy encoding; force UTF-8 so Arabic prints without crashing.
sys.stdout.reconfigure(encoding="utf-8")

# --- Settings ------------------------------------------------------------
RAW_DIR: Path = Path("data/raw")

# A page with fewer characters than this is probably an image (scan) or an empty page.
MIN_CHARS_PER_PAGE: int = 50

# If more than this share of pages are "nearly empty", we call the file a scan.
SCAN_PAGE_RATIO: float = 0.5

# If more than this share of characters are garbage, the text mapping is broken.
GARBAGE_RATIO: float = 0.01

# "الفصل" means "article" in Arabic law. We count it forward and reversed
# to detect right-to-left text that came out backwards.
ARABIC_ARTICLE_WORD: str = "الفصل"

# Garbage = replacement character (U+FFFD) or private-use area (U+E000 to U+F8FF).
GARBAGE_PATTERN = re.compile(r"[\ufffd\ue000-\uf8ff]")
ARABIC_PATTERN = re.compile(r"[\u0600-\u06FF]")  # basic Arabic letters block


def extract_pages(pdf_path: Path) -> list[str]:
    """Return the text of each page (one string per page)."""
    with fitz.open(pdf_path) as doc:           # "with" closes the file automatically
        return [page.get_text("text") for page in doc]


def verdict(pages: list[str], garbage: int, total_chars: int) -> str:
    """Decide if the PDF is usable, a scan, or has broken encoding."""
    if total_chars == 0:
        return "SCAN (no text at all): needs OCR"
    empty_pages = sum(1 for t in pages if len(t.strip()) < MIN_CHARS_PER_PAGE)
    if empty_pages / len(pages) > SCAN_PAGE_RATIO:
        return "SCAN (most pages have no text): needs OCR"
    if garbage / total_chars > GARBAGE_RATIO:
        return "BROKEN ENCODING (garbage characters): needs another source or OCR"
    return "TEXT OK"


def inspect(pdf_path: Path) -> None:
    pages = extract_pages(pdf_path)
    full_text = "\n".join(pages)
    total_chars = len(full_text.strip())

    garbage = len(GARBAGE_PATTERN.findall(full_text))
    arabic_chars = len(ARABIC_PATTERN.findall(full_text))
    empty_pages = sum(1 for t in pages if len(t.strip()) < MIN_CHARS_PER_PAGE)
    article_starts = len(ARTICLE_PATTERN.findall(full_text))

    print("=" * 70)
    print(f"File           : {pdf_path.name}")
    print(f"Pages          : {len(pages)}")
    print(f"Characters     : {total_chars}")
    print(f"Avg chars/page : {total_chars // max(len(pages), 1)}")
    print(f"Nearly empty pages (< {MIN_CHARS_PER_PAGE} chars): {empty_pages}")
    print(f"Garbage chars  : {garbage}")
    print(f"Arabic letters : {arabic_chars}")
    if arabic_chars:
        forward = full_text.count(ARABIC_ARTICLE_WORD)
        backward = full_text.count(ARABIC_ARTICLE_WORD[::-1])
        print(f"Word 'الفصل' forward: {forward} | reversed: {backward}")
    print(f"Article starts found by our regex: {article_starts}")
    print(f"VERDICT        : {verdict(pages, garbage, total_chars)}")

    # Show a sample from the middle of the document (covers pages are not representative).
    middle = pages[len(pages) // 2].strip().replace("\n", " ")
    print(f"Sample (page {len(pages) // 2 + 1}): {middle[:300]}")


def main() -> None:
    pdf_files = sorted(RAW_DIR.glob("*.pdf"))
    if not pdf_files:
        print(f"No PDF found in {RAW_DIR.resolve()}")
        return
    for pdf_path in pdf_files:
        inspect(pdf_path)


if __name__ == "__main__":
    main()