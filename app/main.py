"""FastAPI entry point. .NET equivalent: Program.cs."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from app.config import get_settings
from app.llm.errors import LLMError
from app.llm.factory import get_provider
from app.logging_config import setup_logging
from app.schemas import AnalyzeRequest, AnalyzeResponse, ChatRequest, ChatResponse

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
    version="0.2.0",
    description="Tunisian administrative assistant (LLM foundations, week 1).",
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