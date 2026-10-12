"""FastAPI entry point. .NET equivalent: Program.cs."""
import logging
import time
from contextlib import asynccontextmanager

import psycopg
from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool

from app.config import get_settings
from app.db import connect
from app.embeddings.errors import EmbeddingError
from app.embeddings.factory import get_embedding_provider
from app.llm.errors import LLMError
from app.llm.factory import get_provider
from app.logging_config import setup_logging
from app.rag.generation import RagAnswer, generate_answer
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

settings = get_settings()
setup_logging(settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Code before `yield` runs at startup, code after it at shutdown."""
    logger.info("Starting %s (env=%s)", settings.app_name, settings.environment)
    yield
    logger.info("Shutting down %s", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    version="0.4.0",
    description="Tunisian administrative assistant (LLM foundations, semantic search, grounded answers).",
    lifespan=lifespan,
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
        excerpt=" ".join(hit.content.split())[:300],
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