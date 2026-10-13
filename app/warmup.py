"""Warm-up: run one real (tiny) request on each model, so the first user does not pay for it.

Preloading a model only loads its weights. The first real request still pays a one-time
cost (about 40 s on our machine, see the Ollama logs), so we pay it at startup instead.
"""
import logging
import time

from app.embeddings.factory import get_embedding_provider
from app.llm.factory import get_provider

logger = logging.getLogger(__name__)

# About 600 words: a prompt of realistic size, so the long-prompt path is warmed too.
FILLER_PROMPT = " ".join(["mot"] * 600)


async def warm_up_models() -> None:
    """Embed one text and generate one short answer. Never raises: a failed warm-up is only logged."""
    try:
        started = time.perf_counter()
        await get_embedding_provider().embed_query("warm-up")
        embedded = time.perf_counter()

        provider = get_provider("ollama")
        await provider.complete_messages(
            [
                {"role": "system", "content": "Reply with the single word OK."},
                {"role": "user", "content": FILLER_PROMPT},
            ],
            0.0,
        )
        done = time.perf_counter()
        logger.info(
            "warm-up done: embedding %.1fs, generation %.1fs",
            embedded - started, done - embedded,
        )
    except Exception as exc:  # noqa: BLE001 - startup must never fail because of the warm-up
        logger.warning("warm-up skipped: %s", exc)