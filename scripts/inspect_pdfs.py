"""Step 5: inspect every PDF in data/raw to see if its text can be extracted.

Run from the project root (venv activated):
    python scripts/inspect_pdfs.py
"""
# --- Imports -------------------------------------------------------------
import re
import sys
import unicodedata  # unicodedata.normalize converts presentation forms to normal letters
from pathlib import Path

import pymupdf  # PyMuPDF: reads PDFs (new import name; "fitz" is deprecated)

# Make "app" importable when running this script from the project root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ingestion.chunking import ARTICLE_PATTERN  # noqa: E402  (our Step 3 regex)

# Force UTF-8 so Arabic prints without crashing on Windows.
sys.stdout.reconfigure(encoding="utf-8")

# --- Settings ------------------------------------------------------------
RAW_DIR: Path = Path("data/raw")
MIN_CHARS_PER_PAGE: int = 50   # fewer characters than this = page probably an image
SCAN_PAGE_RATIO: float = 0.5   # more than 50% such pages = we call the file a scan
GARBAGE_RATIO: float = 0.01    # more than 1% garbage characters = broken encoding

# "الفصل" means "article". Counted forward and reversed to detect backwards text.
ARABIC_ARTICLE_WORD: str = "الفصل"

# Garbage = replacement character (U+FFFD) or private-use area (U+E000 to U+F8FF).
GARBAGE_PATTERN = re.compile(r"[\ufffd\ue000-\uf8ff]")
# Normal Arabic letters.
ARABIC_PATTERN = re.compile(r"[\u0600-\u06FF]")
# Arabic "presentation forms": shaped variants that look right but are different characters.
PRESENTATION_PATTERN = re.compile(r"[\ufb50-\ufdff\ufe70-\ufeff]")


def extract_pages(pdf_path: Path) -> list[str]:
    """Return the raw text of each page (one string per page)."""
    with pymupdf.open(pdf_path) as doc:
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
    raw_pages = extract_pages(pdf_path)
    raw_text = "\n".join(raw_pages)

    # NFKC turns Arabic presentation forms (and similar look-alike characters)
    # back into the normal letters. Everything below is measured on the normalized text.
    text = unicodedata.normalize("NFKC", raw_text)
    pages = [unicodedata.normalize("NFKC", p) for p in raw_pages]
    total_chars = len(text.strip())

    presentation_before = len(PRESENTATION_PATTERN.findall(raw_text))
    arabic_after = len(ARABIC_PATTERN.findall(text))
    garbage = len(GARBAGE_PATTERN.findall(text))
    empty_pages = sum(1 for t in pages if len(t.strip()) < MIN_CHARS_PER_PAGE)
    article_starts = len(ARTICLE_PATTERN.findall(text))

    print("=" * 70)
    print(f"File           : {pdf_path.name}")
    print(f"Pages          : {len(pages)}")
    print(f"Characters     : {total_chars}")
    print(f"Avg chars/page : {total_chars // max(len(pages), 1)}")
    print(f"Nearly empty pages (< {MIN_CHARS_PER_PAGE} chars): {empty_pages}")
    print(f"Garbage chars  : {garbage}")
    print(f"Arabic presentation-form chars (before NFKC): {presentation_before}")
    print(f"Arabic letters (after NFKC): {arabic_after}")
    if arabic_after:
        forward = text.count(ARABIC_ARTICLE_WORD)
        backward = text.count(ARABIC_ARTICLE_WORD[::-1])
        print(f"Word 'الفصل' forward: {forward} | reversed: {backward}")
    print(f"Article starts found by our regex (after NFKC): {article_starts}")
    print(f"VERDICT        : {verdict(pages, garbage, total_chars)}")
    if presentation_before > total_chars * 0.05:
        print("NOTE           : presentation forms found. NFKC normalization is REQUIRED before chunking.")

    # Sample from the middle of the document (covers are not representative).
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