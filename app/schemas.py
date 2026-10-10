"""Request and response models for the API (DTOs).

Pydantic validates incoming JSON automatically and documents it in /docs.
"""
from pydantic import BaseModel, Field
from typing import Literal



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





