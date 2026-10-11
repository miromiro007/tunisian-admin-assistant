"""Errors raised by embedding providers."""
from app.llm.errors import LLMError


class EmbeddingError(LLMError):
    """An embedding failure, with the HTTP status to return to the client.

    It is a subclass of LLMError, so any error handler already registered for
    LLMError in the API also covers embedding errors.
    """