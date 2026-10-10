"""Factory: turns a provider name into a provider object."""
from app.llm.base import LLMProvider
from app.llm.errors import LLMError
from app.llm.groq_provider import GroqProvider
from app.llm.ollama_provider import OllamaProvider

_PROVIDERS: dict[str, type[LLMProvider]] = {
    "ollama": OllamaProvider,
    "groq": GroqProvider,
}


def get_provider(name: str) -> LLMProvider:
    """Return a provider instance, or raise a 400 error for an unknown name."""
    provider_class = _PROVIDERS.get(name)
    if provider_class is None:
        raise LLMError(f"Unknown provider '{name}'. Use: {', '.join(_PROVIDERS)}.", 400)
    return provider_class()