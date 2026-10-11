"""Abstract embedding provider: the common 'plug shape' for every embedding backend."""
from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """Every embedding provider must implement these four members."""

    name: str = ""  # "ollama"

    @property
    @abstractmethod
    def model(self) -> str:
        """Name of the embedding model."""

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Size of the vectors this provider returns (must match the database column)."""

    @abstractmethod
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed texts that will be STORED (chunks). One vector per text, same order."""

    @abstractmethod
    async def embed_query(self, text: str) -> list[float]:
        """Embed a user question used to SEARCH. Returns a single vector."""