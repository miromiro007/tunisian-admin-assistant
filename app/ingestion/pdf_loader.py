"""PDF loading and cleaning: PDF file -> clean text, one entry per page.

Steps applied to every page:
  1. NFKC normalization (Arabic presentation forms -> normal letters)
  2. remove garbage and invisible characters
  3. Arabic: remove diacritics and tatweel (so user questions match the text)
  4. French: rejoin words hyphenated at the end of a line
  5. clean whitespace, drop lines with only punctuation, drop a lone page number
"""
import logging
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import pymupdf

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
# A page number alone on the first line.
LONE_PAGE_NUMBER = re.compile(r"\d{1,4}")


@dataclass(frozen=True)
class PageText:
    """The clean text of one PDF page, with what we need to cite it later."""

    document: str   # file name, e.g. "code_du_travail_ar_2004.pdf"
    page: int       # page number, starting at 1 (as in a PDF viewer)
    text: str       # cleaned text
    language: str   # "ar" or "fr"


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


def load_pdf(path: Path) -> list[PageText]:
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

    logger.info("%s: %d non-empty pages loaded (%s)", path.name, len(pages), language)
    return pages