"""Generation service: question + retrieved chunks -> grounded answer with validated citations."""
import logging
import re
import time
from dataclasses import dataclass

from app.llm.base import LLMProvider
from app.rag.context import ARABIC_LETTERS, DEFAULT_MAX_TOKENS, ContextSource, build_context
from app.rag.prompts import (
    NO_ANSWER_MARKER,
    QUESTION_LABEL,
    REFUSAL,
    REMINDER,
    SOURCES_LABEL,
    SYSTEM,
)
from app.search import SearchHit

logger = logging.getLogger(__name__)

CITATION = re.compile(r"\[(\d+)\]")
MIN_ANSWER_CHARS = 3  # letters/digits needed besides the [n] markers for an answer to count


@dataclass(frozen=True)
class RagAnswer:
    """The result of one RAG generation."""

    answer: str
    refused: bool
    refusal_reason: str | None          # "no_sources", "below_threshold", "model_declined", "empty_answer"
    language: str                       # language of the question: "fr" or "ar"
    sources: list[ContextSource]        # every source that was shown to the model
    cited_numbers: list[int]            # valid [n] found in the answer, in order
    invalid_citations: list[int]        # [n] that do not match any source (fake citations)
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int


def detect_language(question: str) -> str:
    """'ar' if the question contains Arabic letters, else 'fr'."""
    return "ar" if ARABIC_LETTERS.search(question) else "fr"


def build_messages(question: str, sources_text: str, language: str) -> list[dict[str, str]]:
    """System rules, then sources + question + a reminder of the rules (last thing read)."""
    user = (
        f"{SOURCES_LABEL[language]}:\n{sources_text}\n\n"
        f"{QUESTION_LABEL[language]}: {question}\n\n"
        f"{REMINDER[language]}"
    )
    return [
        {"role": "system", "content": SYSTEM[language]},
        {"role": "user", "content": user},
    ]


def parse_citations(text: str, source_count: int) -> tuple[list[int], list[int]]:
    """Return (valid, invalid) citation numbers found in the text, without duplicates."""
    valid: list[int] = []
    invalid: list[int] = []
    for match in CITATION.finditer(text):
        number = int(match.group(1))
        target = valid if 1 <= number <= source_count else invalid
        if number not in target:
            target.append(number)
    return valid, invalid


def has_answer_text(text: str) -> bool:
    """False if the text is only citation markers like '[1]' (no actual answer)."""
    without_citations = CITATION.sub("", text)
    return len(re.findall(r"\w", without_citations)) >= MIN_ANSWER_CHARS


def _refusal(
    language: str, reason: str, sources: list[ContextSource], started: float,
    prompt_tokens: int = 0, completion_tokens: int = 0,
) -> RagAnswer:
    return RagAnswer(
        answer=REFUSAL[language], refused=True, refusal_reason=reason, language=language,
        sources=sources, cited_numbers=[], invalid_citations=[],
        prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
        latency_ms=int((time.perf_counter() - started) * 1000),
    )


async def generate_answer(
    provider: LLMProvider,
    question: str,
    hits: list[SearchHit],
    *,
    min_score: float | None = None,
    max_context_tokens: int = DEFAULT_MAX_TOKENS,
    temperature: float = 0.0,
) -> RagAnswer:
    """Answer the question from the hits, or refuse.

    Refusal BEFORE the LLM (saves time and avoids a made-up answer):
      - no hits at all
      - best score below `min_score`
    Refusal AFTER the LLM:
      - the model answered exactly NO_ANSWER ("model_declined")
      - the model answered with citation markers only ("empty_answer")
    """
    started = time.perf_counter()
    language = detect_language(question)

    if not hits:
        return _refusal(language, "no_sources", [], started)
    if min_score is not None and hits[0].score < min_score:
        logger.info("refused before the LLM: best score %.3f < %.3f", hits[0].score, min_score)
        return _refusal(language, "below_threshold", [], started)

    context = build_context(hits, max_tokens=max_context_tokens)
    messages = build_messages(question, context.text, language)
    completion = await provider.complete_messages(messages, temperature)
    raw = completion.text.strip()

    if NO_ANSWER_MARKER in raw:
        logger.info("model declined, raw output: %r", raw[:300])
        return _refusal(
            language, "model_declined", context.sources, started,
            completion.prompt_tokens, completion.completion_tokens,
        )
    if not has_answer_text(raw):
        logger.warning("empty answer (citation markers only): %r", raw[:80])
        return _refusal(
            language, "empty_answer", context.sources, started,
            completion.prompt_tokens, completion.completion_tokens,
        )

    valid, invalid = parse_citations(raw, len(context.sources))
    if invalid:
        logger.warning("fake citations %s (only %d sources)", invalid, len(context.sources))
    return RagAnswer(
        answer=raw, refused=False, refusal_reason=None, language=language,
        sources=context.sources, cited_numbers=valid, invalid_citations=invalid,
        prompt_tokens=completion.prompt_tokens, completion_tokens=completion.completion_tokens,
        latency_ms=int((time.perf_counter() - started) * 1000),
    )