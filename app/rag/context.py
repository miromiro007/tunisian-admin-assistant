"""Context builder: turn search hits into numbered sources that fit a token budget."""
import math
import re
from dataclasses import dataclass

from app.search import SearchHit

ARABIC_LETTERS = re.compile(r"[\u0600-\u06FF]")

# Rough sizes: Arabic needs more tokens per character than French.
# These are estimates: scripts/context_budget_demo.py compares them with the real count.
FR_CHARS_PER_TOKEN = 2.8
AR_CHARS_PER_TOKEN = 2.5
SEPARATOR_TOKENS = 2  # the blank line between two sources

DEFAULT_MAX_TOKENS = 3000       # budget for the sources only (not the question or the answer)
DEFAULT_MAX_CHARS_PER_CHUNK = 1500


@dataclass(frozen=True)
class ContextSource:
    """One numbered source of the prompt, linked to the chunk it came from."""

    number: int       # the [n] the model will cite
    hit: SearchHit    # the chunk (id, document, law_title, article, page, content)


@dataclass(frozen=True)
class BuiltContext:
    """The text to put in the prompt, and what is in it."""

    text: str
    sources: list[ContextSource]
    estimated_tokens: int
    dropped: int      # hits that did not fit in the budget


def estimate_tokens(text: str) -> int:
    """Estimate the number of tokens of a text (conservative, never 0 for a non-empty text)."""
    if not text:
        return 0
    arabic_share = len(ARABIC_LETTERS.findall(text)) / len(text)
    chars_per_token = AR_CHARS_PER_TOKEN if arabic_share > 0.3 else FR_CHARS_PER_TOKEN
    return math.ceil(len(text) / chars_per_token)


def source_label(hit: SearchHit) -> str:
    """'LOI N°60-30 ... | Art. 15 | p.195' (falls back to the file name without a law title)."""
    parts = [hit.law_title or hit.document]
    if hit.article:
        parts.append(f"Art. {hit.article}")
    if hit.page is not None:
        parts.append(f"p.{hit.page}")
    return " | ".join(parts)


def build_context(
    hits: list[SearchHit],
    *,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    max_chars_per_chunk: int = DEFAULT_MAX_CHARS_PER_CHUNK,
) -> BuiltContext:
    """Number the hits [1], [2]... in relevance order and stop when the budget is full.

    The first hit is always kept (cut if needed): an empty context would be useless.
    """
    blocks: list[str] = []
    sources: list[ContextSource] = []
    used = 0

    for hit in hits:
        number = len(sources) + 1
        body = " ".join(hit.content.split())[:max_chars_per_chunk]
        block = f"[{number}] {source_label(hit)}\n{body}"
        cost = estimate_tokens(block) + SEPARATOR_TOKENS

        if used + cost > max_tokens:
            if sources:
                break  # budget full: the remaining hits are the least relevant ones
            # The very first chunk alone is too big: cut it to fit.
            target = max(max_tokens - SEPARATOR_TOKENS, 1)
            keep = int(len(block) * target / estimate_tokens(block))
            block = block[:keep]
            cost = estimate_tokens(block) + SEPARATOR_TOKENS

        blocks.append(block)
        sources.append(ContextSource(number=number, hit=hit))
        used += cost

    text = "\n\n".join(blocks)
    return BuiltContext(
        text=text,
        sources=sources,
        estimated_tokens=estimate_tokens(text),
        dropped=len(hits) - len(sources),
    )