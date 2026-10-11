"""Chunking: split a document's text into chunks that keep their metadata.

Two strategies:
  - chunk_by_article: one chunk per legal article ("Article 12", "الفصل 12")
  - chunk_fixed_size: fixed-size windows with overlap (fallback for text without articles)
"""
import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Chunk:
    """One piece of a document, with what we need to cite it later.

    frozen=True makes it immutable, like a C# record.
    """

    text: str                    # the chunk content
    document: str                # source document name, e.g. "code_du_travail.pdf"
    page: int | None = None      # page number where the chunk starts (None if unknown)
    article: str | None = None   # article label, e.g. "12" (None for non-article chunks)
    language: str = "fr"         # "fr" or "ar"
    metadata: dict = field(default_factory=dict)  # room for extra info later


# Detects the START of an article, at the beginning of a line.
#   French : "Article 12", "Article 12 bis", "Article premier", "Art. 12"
#   Arabic : "الفصل 12", "الفصل الأول", "فصل 12"
# (?m) = MULTILINE: ^ matches at the start of every line, not only the start of the text.
# The captured group (1) is the article label (the number or word after "Article").
ARTICLE_PATTERN = re.compile(
    r"(?m)^\s*(?:Article|Art\.|الفصل|فصل)\s+"
    r"(premier|\d+(?:\s*(?:bis|ter|quater))?|[\u0621-\u064A]+)"
)


def chunk_by_article(
    text: str,
    document: str,
    page: int | None = None,
    language: str = "fr",
    max_chars: int = 1500,
    overlap: int = 150,
) -> list[Chunk]:
    """Split text into one chunk per article.

    If an article is longer than max_chars, it is split further with a fixed-size window
    (the article label is kept on each piece). Text before the first article is kept as a
    chunk without an article label (title, preamble).
    """
    matches = list(ARTICLE_PATTERN.finditer(text))
    if not matches:
        # No article found: fall back to fixed-size chunking.
        return chunk_fixed_size(text, document, page, language, max_chars, overlap)

    chunks: list[Chunk] = []

    # 1) Preamble: everything before the first article.
    preamble = text[: matches[0].start()].strip()
    if preamble:
        chunks.extend(chunk_fixed_size(preamble, document, page, language, max_chars, overlap))

    # 2) Each article goes from its own start to the start of the next article.
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        article_text = text[start:end].strip()
        label = re.sub(r"\s+", " ", match.group(1)).strip()  # normalize spaces: "12  bis" -> "12 bis"

        if len(article_text) <= max_chars:
            chunks.append(Chunk(article_text, document, page, label, language))
        else:
            # Very long article: split it, keep the same article label on every piece.
            for piece in chunk_fixed_size(article_text, document, page, language, max_chars, overlap):
                chunks.append(
                    Chunk(piece.text, document, page, label, language)
                )
    return chunks


def chunk_fixed_size(
    text: str,
    document: str,
    page: int | None = None,
    language: str = "fr",
    chunk_size: int = 1000,
    overlap: int = 100,
) -> list[Chunk]:
    """Split text into windows of chunk_size characters, overlapping by `overlap`.

    Example with chunk_size=10, overlap=3 on "ABCDEFGHIJKLMNOP":
        "ABCDEFGHIJ", "HIJKLMNOP"  (the last 3 characters of chunk 1 start chunk 2)
    """
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    text = text.strip()
    chunks: list[Chunk] = []
    step = chunk_size - overlap  # how far the window moves each time
    start = 0
    while start < len(text):
        piece = text[start : start + chunk_size].strip()
        if piece:  # never keep an empty chunk (embedding an empty string would fail later)
            chunks.append(Chunk(piece, document, page, None, language))
        if start + chunk_size >= len(text):
            break  # last window reached the end
        start += step
    return chunks