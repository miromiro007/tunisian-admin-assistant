"""PDF loading and cleaning: PDF file -> clean text, one entry per page.

Steps applied to every page (clean_text):
  1. NFKC normalization (Arabic presentation forms -> normal letters)
  2. remove garbage and invisible characters
  3. Arabic: remove diacritics and tatweel (so user questions match the text)
  4. French: rejoin words hyphenated at the end of a line
  5. clean whitespace, drop lines with only punctuation, drop a lone page number

Then, on the whole list of pages (strip_repeated_lines):
  6. remove page numbers at the edges of the page
  7. remove running headers/footers (first/last line repeated on many pages)
     and keep the removed header in PageText.header
"""
import logging
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, replace
from pathlib import Path

import pymupdf

from app.ingestion.chunking import ARTICLE_PATTERN

logger = logging.getLogger(__name__)

# "code_du_travail_ar_2004.pdf" -> "ar" ; "cnss_..._fr_2007.pdf" -> "fr"
LANGUAGE_FROM_NAME = re.compile(r"_(ar|fr)(?:_\d{4})?\.pdf$", re.IGNORECASE)

# Replacement character (U+FFFD) and private-use area (U+E000 to U+F8FF): broken mappings.
GARBAGE_CHARS = re.compile(r"[\ufffd\ue000-\uf8ff]")
# Invisible direction/format marks that add noise without meaning.
INVISIBLE_CHARS = re.compile(r"[\u200b-\u200f\u202a-\u202e\u2066-\u2069\ufeff]")
# Arabic marks above/below letters (fatha, damma, shadda...) and the stretching character.
ARABIC_SPACE_BEFORE_MARK = re.compile(r"[ \t]+(?=[\u064b-\u0652\u0670])")
ARABIC_MARKS = re.compile(r"[\u064b-\u0652\u0670\u0640]")
# French word cut with a hyphen at the end of a line: "condi-\ntions".
HYPHEN_LINE_BREAK = re.compile(r"(?<=[a-zà-ÿ])-\n(?=[a-zà-ÿ])")
# A page number alone on a line.
LONE_PAGE_NUMBER = re.compile(r"\d{1,4}")

LAW_TITLE_KEYWORDS = re.compile(
    r"\b(?:LOI|DECRET|ARRETE|CODE)\b|قانون|أمر|مجلة", re.IGNORECASE
)

# ---- Header/footer detection settings (chosen from the numbers of find_repeated_lines.py) ----
EDGE_NUMBER_LINES = 2     # page numbers are searched in the first and last 2 lines
HEADER_MIN_SHARE = 0.10   # a first/last line on >= 10% of pages is a header/footer
HEADER_MIN_PAGES = 3      # ...and on at least 3 pages (avoids deleting things in tiny PDFs)
HEADER_MAX_CHARS = 120    # a longer line is a real sentence, never a header


@dataclass(frozen=True)
class PageText:
    """The clean text of one PDF page, with what we need to cite it later."""

    document: str   # file name, e.g. "code_du_travail_ar_2004.pdf"
    page: int       # page number, starting at 1 (as in a PDF viewer)
    text: str       # cleaned text
    language: str   # "ar" or "fr"
    header: str | None = None  # running header removed from the top of this page (if any)


def language_from_filename(path: Path) -> str:
    """Read the language from the file name suffix (_ar or _fr)."""
    match = LANGUAGE_FROM_NAME.search(path.name)
    if not match:
        raise ValueError(
            f"Cannot find the language in '{path.name}'. "
            "Name the file like 'name_ar_2004.pdf' or 'name_fr.pdf'."
        )
    return match.group(1).lower()


def clean_text(text: str) -> str:
    """Clean the text of one page (pure function: same input, same output)."""
    text = unicodedata.normalize("NFKC", text)
    text = GARBAGE_CHARS.sub("", text)
    text = INVISIBLE_CHARS.sub("", text)
    text = ARABIC_SPACE_BEFORE_MARK.sub("", text)  # "تسل ّط" -> "تسلّط" before removing marks
    text = ARABIC_MARKS.sub("", text)
    text = HYPHEN_LINE_BREAK.sub("", text)
    text = re.sub(r"[ \t]+", " ", text)

    lines = [line.strip() for line in text.split("\n")]
    # Keep only lines that contain at least one letter or digit (\w).
    lines = [line for line in lines if re.search(r"\w", line)]
    # Drop a page number that sits alone on the first line (common in these PDFs).
    if lines and LONE_PAGE_NUMBER.fullmatch(lines[0]):
        lines = lines[1:]
    return "\n".join(lines)


# ---------- repeated headers and footers (needs ALL pages, not one) ----------


def _line_key(line: str) -> str:
    """Digits -> '#' so 'Page 321' and 'Page 322' count as the same line."""
    return re.sub(r"\s+", " ", re.sub(r"\d+", "#", line)).strip()


def _is_protected(line: str) -> bool:
    """A line we must never remove: an article heading or a real sentence."""
    return len(line) > HEADER_MAX_CHARS or ARTICLE_PATTERN.match(line) is not None


def _strip_edge_numbers(lines: list[str]) -> list[str]:
    """Remove lone page numbers found in the first or last EDGE_NUMBER_LINES lines."""
    count = len(lines)
    edge_indexes = {*range(min(EDGE_NUMBER_LINES, count)), *range(max(0, count - EDGE_NUMBER_LINES), count)}
    return [
        line
        for index, line in enumerate(lines)
        if not (index in edge_indexes and LONE_PAGE_NUMBER.fullmatch(line))
    ]


def find_repeated_edge_keys(pages_lines: list[list[str]]) -> set[str]:
    """Keys of the FIRST or LAST line that repeat on enough pages.

    Only the first and the last line of each page are candidates. A line in second
    position (like a signature before a footer) is never counted, so it is never removed.
    """
    counter: Counter[str] = Counter()
    for lines in pages_lines:
        if not lines:
            continue
        # set(): a key counts once per page.
        keys = {_line_key(line) for line in (lines[0], lines[-1]) if not _is_protected(line)}
        counter.update(keys)

    total = len(pages_lines)
    return {
        key
        for key, count in counter.items()
        if count >= HEADER_MIN_PAGES and count / total >= HEADER_MIN_SHARE
    }


def strip_repeated_lines(pages: list[PageText]) -> list[PageText]:
    """Remove page numbers and running headers/footers from every page.

    The first header removed from a page is kept in PageText.header (used later as a
    law title). Pages that become empty are dropped.
    """
    if not pages:
        return []

    all_lines = [_strip_edge_numbers(page.text.split("\n")) for page in pages]
    repeated = find_repeated_edge_keys(all_lines)
    logger.info("repeated header/footer patterns found: %d", len(repeated))

    cleaned: list[PageText] = []
    removed = 0
    for page, lines in zip(pages, all_lines):
        header: str | None = None
        # Top: remove repeated lines one by one (a header can be 2 lines long).
        while lines and _line_key(lines[0]) in repeated and not _is_protected(lines[0]):
            if header is None and LAW_TITLE_KEYWORDS.search(lines[0]):
                header = lines[0]
            lines = lines[1:]
            removed += 1
        # Bottom: same, for footers.
        while lines and _line_key(lines[-1]) in repeated and not _is_protected(lines[-1]):
            lines = lines[:-1]
            removed += 1

        if not lines:
            logger.debug("%s: page %d is empty after header removal", page.document, page.page)
            continue
        cleaned.append(replace(page, text="\n".join(lines), header=header))

    logger.info("%d header/footer lines removed from %d pages", removed, len(pages))
    return cleaned


def load_pdf(path: Path, remove_repeated: bool = True) -> list[PageText]:
    """Read a PDF and return one clean PageText per non-empty page."""
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")
    language = language_from_filename(path)

    pages: list[PageText] = []
    with pymupdf.open(path) as doc:
        for index, page in enumerate(doc, start=1):  # PDF pages start at 1
            text = clean_text(page.get_text("text"))
            if not text:
                logger.debug("%s: page %d is empty, skipped", path.name, index)
                continue
            pages.append(PageText(path.name, index, text, language))

    if remove_repeated:
        pages = strip_repeated_lines(pages)

    logger.info("%s: %d non-empty pages loaded (%s)", path.name, len(pages), language)
    return pages