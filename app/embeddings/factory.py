"""Factory: turns a provider name into an embedding provider object."""
from app.config import get_settings
from app.embeddings.base import EmbeddingProvider
from app.embeddings.errors import EmbeddingError
from app.embeddings.ollama_embedder import OllamaEmbeddingProvider

_PROVIDERS: dict[str, type[EmbeddingProvider]] = {
    "ollama": OllamaEmbeddingProvider,
}


def get_embedding_provider(name: str | None = None) -> EmbeddingProvider:
    """Return a provider instance. Without a name, use EMBEDDING_PROVIDER from settings."""
    provider_name = name or get_settings().embedding_provider
    provider_class = _PROVIDERS.get(provider_name)
    if provider_class is None:
        raise EmbeddingError(
            f"Unknown embedding provider '{provider_name}'. Use: {', '.join(_PROVIDERS)}.", 400
        )
    return provider_class()