"""Request and response models for the API (DTOs).

Pydantic validates incoming JSON automatically and documents it in /docs.
"""
from pydantic import BaseModel, Field, field_validator
from typing import Literal
from app.ingestion.configs import CONFIGS, DEFAULT_CONFIG



class ChatRequest(BaseModel):
    """Body of POST /chat."""

    # min_length=1: an empty question is rejected with a 422 error.
    # max_length=2000: protects us from huge (expensive) prompts.
    question: str = Field(..., min_length=1, max_length=2000,
                          description="The user's question.")

    # Which provider to use. Only "ollama" for now; "groq" comes in Step 4.
    provider: Literal["ollama", "groq"] = Field(
        default="ollama", description="LLM provider: 'ollama' (local) or 'groq' (cloud)."
    )

    # Low temperature = stable answers. ge/le = allowed range (0 to 2).
    temperature: float = Field(default=0.2, ge=0.0, le=2.0,
                               description="Randomness of the answer.")


class ChatResponse(BaseModel):
    """Body returned by POST /chat."""

    answer: str
    provider: str
    model: str
    # Exact token counts reported by the provider.
    prompt_tokens: int
    completion_tokens: int
    # Time taken for the LLM call, in milliseconds.
    latency_ms: int


class AnalyzeRequest(BaseModel):
    """Body of POST /analyze."""

    question: str = Field(..., min_length=1, max_length=2000)
    provider: Literal["ollama", "groq"] = Field(default="ollama")


class QuestionAnalysis(BaseModel):
    """Structured result extracted from a question. The LLM must fill this shape."""

    # Literal = only these exact values are allowed. Anything else fails validation.
    theme: Literal["labor_law", "cnss", "company_creation", "taxes", "other"]
    # A short sentence describing what the user wants to do.
    intent: str = Field(..., min_length=1, max_length=200)
    # Between 1 and 8 important words.
    keywords: list[str] = Field(..., min_length=1, max_length=8)

class AnalyzeResponse(BaseModel):
    """Body returned by POST /analyze."""

    analysis: QuestionAnalysis
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int

class SearchRequest(BaseModel):
    """Body of POST /search."""

    question: str = Field(min_length=3, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=20)
    chunk_config: str = DEFAULT_CONFIG
    language: Literal["fr", "ar"] | None = None  # None = search in both languages

    @field_validator("chunk_config")
    @classmethod
    def chunk_config_must_exist(cls, value: str) -> str:
        if value not in CONFIGS:
            raise ValueError(f"unknown chunk_config '{value}', choose one of {list(CONFIGS)}")
        return value


class SearchHitResponse(BaseModel):
    """One chunk returned by the search (also the future citation)."""

    score: float
    document: str
    page: int | None
    article: str | None
    language: str
    chunk_config: str
    content: str


class SearchResponse(BaseModel):
    question: str
    chunk_config: str
    hits: list[SearchHitResponse]


class AskRequest(BaseModel):
    """Body of POST /ask."""

    question: str = Field(min_length=3, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=10)
    chunk_config: str = DEFAULT_CONFIG
    language: Literal["fr", "ar"] | None = None  # None = search in both languages
    provider: Literal["ollama", "groq"] = "ollama"

    @field_validator("chunk_config")
    @classmethod
    def chunk_config_must_exist(cls, value: str) -> str:
        if value not in CONFIGS:
            raise ValueError(f"unknown chunk_config '{value}', choose one of {list(CONFIGS)}")
        return value


class SourceResponse(BaseModel):
    """One source shown to the model. `cited` is True if the answer cites it."""

    number: int                  # the [n] used in the answer
    chunk_id: int | None
    document: str
    law_title: str | None
    article: str | None
    page: int | None
    language: str
    score: float                 # cosine similarity of the retrieval
    excerpt: str                 # first characters of the chunk, for display
    cited: bool


class TimingsResponse(BaseModel):
    """Time spent in each stage, in milliseconds."""

    embed_ms: int
    retrieval_ms: int
    generation_ms: int
    total_ms: int


class AskResponse(BaseModel):
    """Body returned by POST /ask."""

    question: str
    answer: str
    refused: bool
    refusal_reason: str | None   # no_sources | below_threshold | model_declined | empty_answer
    language: str                # language of the answer: "fr" or "ar"
    best_score: float | None     # best retrieval score (explains a refusal)
    citations: list[SourceResponse]   # only the sources the answer cites
    sources: list[SourceResponse]     # every source shown to the model
    invalid_citations: list[int]      # [n] the model wrote that match no source
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    timings: TimingsResponse





