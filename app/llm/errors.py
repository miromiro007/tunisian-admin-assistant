"""Errors shared by all providers."""


class LLMError(Exception):
    """Our own error type, carrying the HTTP status to return to the client."""

    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code
        