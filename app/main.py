"""FastAPI entry point. .NET equivalent: Program.cs."""
import asyncio
import json
import logging
import time
from contextlib import asynccontextmanager

import psycopg
from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.config import get_settings
from app.db import connect
from app.embeddings.errors import EmbeddingError
from app.embeddings.factory import get_embedding_provider
from app.llm.errors import LLMError
from app.llm.factory import get_provider
from app.logging_config import setup_logging
from app.rag.generation import RagAnswer, generate_answer, generate_answer_stream
from app.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    AskRequest,
    AskResponse,
    ChatRequest,
    ChatResponse,
    SearchHitResponse,
    SearchRequest,
    SearchResponse,
    SourceResponse,
    TimingsResponse,
)
from app.search import SearchHit, search_chunks
from app.warmup import warm_up_models

settings = get_settings()
setup_logging(settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Code before `yield` runs at startup, code after it at shutdown."""
    logger.info("Starting %s (env=%s)", settings.app_name, settings.environment)
    # Background task: the API accepts requests immediately, the models warm up meanwhile.
    warmup_task = asyncio.create_task(warm_up_models()) if settings.rag_warmup else None
    yield
    if warmup_task is not None:
        warmup_task.cancel()
    logger.info("Shutting down %s", settings.app_name)

app = FastAPI(
    title=settings.app_name,
    version="0.4.0",
    description="Tunisian administrative assistant (LLM foundations, semantic search, grounded answers).",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    """Liveness probe: tells Docker/cloud platforms that the app is up."""
    return {"status": "ok", "environment": settings.environment}


@app.post("/chat", response_model=ChatResponse, tags=["chat"])
async def chat(request: ChatRequest) -> ChatResponse:
    """Send a question to the chosen provider and return the answer."""
    logger.info("POST /chat provider=%s", request.provider)
    try:
        provider = get_provider(request.provider)
        return await provider.chat(request.question, request.temperature)
    except LLMError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@app.post("/analyze", response_model=AnalyzeResponse, tags=["chat"])
async def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    """Extract theme, intent and keywords with the chosen provider."""
    logger.info("POST /analyze provider=%s", request.provider)
    try:
        provider = get_provider(request.provider)
        return await provider.analyze(request.question)
    except LLMError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


def _search_database(
    query_vector: list[float], chunk_config: str, top_k: int, language: str | None
) -> list[SearchHit]:
    """Blocking database work (psycopg is synchronous): run it in a worker thread."""
    with connect() as connection:
        return search_chunks(
            connection, query_vector, chunk_config=chunk_config, top_k=top_k, language=language
        )


@app.post("/search", response_model=SearchResponse, tags=["search"])
async def search(request: SearchRequest) -> SearchResponse:
    """Find the chunks closest in meaning to the question (no LLM involved yet)."""
    logger.info(
        "POST /search config=%s top_k=%d language=%s",
        request.chunk_config, request.top_k, request.language,
    )
    try:
        embedder = get_embedding_provider()
        query_vector = await embedder.embed_query(request.question)
    except EmbeddingError as exc:
        raise HTTPException(status_code=getattr(exc, "status_code", 502), detail=str(exc))

    try:
        hits = await run_in_threadpool(
            _search_database, query_vector, request.chunk_config, request.top_k, request.language
        )
    except (psycopg.Error, RuntimeError):
        logger.exception("Database error during /search")
        raise HTTPException(status_code=503, detail="The database is not available.")

    return SearchResponse(
        question=request.question,
        chunk_config=request.chunk_config,
        hits=[SearchHitResponse(**vars(hit)) for hit in hits],
    )


def _to_source(source, cited: bool) -> SourceResponse:
    """Convert a ContextSource (chunk + number) into the API model."""
    hit = source.hit
    return SourceResponse(
        number=source.number,
        chunk_id=hit.id,
        document=hit.document,
        law_title=hit.law_title,
        article=hit.article,
        page=hit.page,
        language=hit.language,
        score=hit.score,
        excerpt=" ".join(hit.content.split())[:1500],
        cited=cited,
    )


def _build_ask_response(
    question: str, result: RagAnswer, hits: list[SearchHit],
    provider_name: str, model: str, timings: TimingsResponse,
) -> AskResponse:
    sources = [_to_source(s, s.number in result.cited_numbers) for s in result.sources]
    return AskResponse(
        question=question,
        answer=result.answer,
        refused=result.refused,
        refusal_reason=result.refusal_reason,
        language=result.language,
        best_score=hits[0].score if hits else None,
        citations=[s for s in sources if s.cited],
        sources=sources,
        invalid_citations=result.invalid_citations,
        provider=provider_name,
        model=model,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        timings=timings,
    )


@app.post("/ask", response_model=AskResponse, tags=["rag"])
async def ask(request: AskRequest) -> AskResponse:
    """Answer a question from the documents, with citations, or refuse."""
    started = time.perf_counter()
    logger.info(
        "POST /ask config=%s top_k=%d language=%s provider=%s question_chars=%d",
        request.chunk_config, request.top_k, request.language, request.provider,
        len(request.question),
    )

    # 1) Embed the question.
    try:
        embedder = get_embedding_provider()
        query_vector = await embedder.embed_query(request.question)
    except EmbeddingError as exc:
        raise HTTPException(status_code=getattr(exc, "status_code", 502), detail=str(exc))
    embedded = time.perf_counter()

    # 2) Retrieve (blocking database work, so in a worker thread).
    try:
        hits = await run_in_threadpool(
            _search_database, query_vector, request.chunk_config, request.top_k, request.language
        )
    except (psycopg.Error, RuntimeError):
        logger.exception("Database error during /ask")
        raise HTTPException(status_code=503, detail="The database is not available.")
    retrieved = time.perf_counter()

    # 3) Generate the grounded answer (or refuse).
    try:
        provider = get_provider(request.provider)
        result = await generate_answer(
            provider, request.question, hits,
            min_score=settings.rag_min_score,
            max_context_tokens=settings.rag_max_context_tokens,
        )
    except LLMError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))
    finished = time.perf_counter()

    timings = TimingsResponse(
        embed_ms=int((embedded - started) * 1000),
        retrieval_ms=int((retrieved - embedded) * 1000),
        generation_ms=int((finished - retrieved) * 1000),
        total_ms=int((finished - started) * 1000),
    )
    logger.info(
        "ask done refused=%s reason=%s cited=%s invalid=%s total_ms=%d",
        result.refused, result.refusal_reason, result.cited_numbers,
        result.invalid_citations, timings.total_ms,
    )
    return _build_ask_response(request.question, result, hits, provider.name, provider.model, timings)

def _sse(event: str, data: dict) -> str:
    """Format one Server-Sent Event: 'event:' line, 'data:' line, blank line."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.post("/ask/stream", tags=["rag"])
async def ask_stream(request: AskRequest) -> StreamingResponse:
    """Same as /ask, but the answer is streamed as Server-Sent Events.

    Events: sources, token (many), done (full AskResponse), or error.
    """
    started = time.perf_counter()
    logger.info(
        "POST /ask/stream config=%s top_k=%d language=%s provider=%s question_chars=%d",
        request.chunk_config, request.top_k, request.language, request.provider,
        len(request.question),
    )

    # Errors BEFORE the first byte can still use real HTTP status codes.
    try:
        embedder = get_embedding_provider()
        query_vector = await embedder.embed_query(request.question)
    except EmbeddingError as exc:
        raise HTTPException(status_code=getattr(exc, "status_code", 502), detail=str(exc))
    embedded = time.perf_counter()

    try:
        hits = await run_in_threadpool(
            _search_database, query_vector, request.chunk_config, request.top_k, request.language
        )
    except (psycopg.Error, RuntimeError):
        logger.exception("Database error during /ask/stream")
        raise HTTPException(status_code=503, detail="The database is not available.")
    retrieved = time.perf_counter()

    try:
        provider = get_provider(request.provider)
    except LLMError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))

    async def event_stream():
        first_token: float | None = None
        try:
            async for event in generate_answer_stream(
                provider, request.question, hits,
                min_score=settings.rag_min_score,
                max_context_tokens=settings.rag_max_context_tokens,
            ):
                if event.kind == "sources":
                    items = [_to_source(s, False).model_dump() for s in event.sources]
                    yield _sse("sources", {"sources": items})
                elif event.kind == "token":
                    if first_token is None:
                        first_token = time.perf_counter()
                    yield _sse("token", {"text": event.text})
                elif event.kind == "final" and event.answer is not None:
                    finished = time.perf_counter()
                    timings = TimingsResponse(
                        embed_ms=int((embedded - started) * 1000),
                        retrieval_ms=int((retrieved - embedded) * 1000),
                        generation_ms=int((finished - retrieved) * 1000),
                        total_ms=int((finished - started) * 1000),
                        first_token_ms=(
                            int((first_token - started) * 1000) if first_token is not None else None
                        ),
                    )
                    logger.info(
                        "ask/stream done refused=%s reason=%s cited=%s total_ms=%d first_token_ms=%s",
                        event.answer.refused, event.answer.refusal_reason,
                        event.answer.cited_numbers, timings.total_ms, timings.first_token_ms,
                    )
                    body = _build_ask_response(
                        request.question, event.answer, hits, provider.name, provider.model, timings
                    )
                    yield _sse("done", body.model_dump())
        except LLMError as exc:
            # The HTTP status is already sent: the error travels as an event.
            yield _sse("error", {"status": exc.status_code, "detail": str(exc)})
        except Exception:
            logger.exception("Unexpected error while streaming /ask/stream")
            yield _sse("error", {"status": 500, "detail": "Unexpected error."})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

