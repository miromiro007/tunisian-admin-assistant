"""Application configuration, loaded from environment variables / .env file."""
from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed settings. Each field is filled from the env var with the same name."""

    # --- Application ---
    app_name: str = "Tunisian Admin Assistant"
    environment: str = "dev"  # dev | prod
    log_level: str = "INFO"   # DEBUG | INFO | WARNING | ERROR

    # --- Local LLM (Ollama) ---
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"

    # --- Cloud LLM (Groq) ---
    # SecretStr hides the value when printed or logged: it shows '**********'.
    # No default value: the key can be missing if you only use Ollama,
    # so we make it optional with an empty default.
    groq_api_key: SecretStr = SecretStr("")
    groq_model: str = "llama-3.3-70b-versatile"

    # --- Embeddings (Week 2) ---
    embedding_provider: str = "ollama"        # which implementation to use
    embedding_model: str = "bge-m3"
    embedding_dimensions: int = 1024          # must match the vector(1024) column
    embedding_batch_size: int = 32            # texts sent to the model per request
    embedding_timeout_seconds: float = 120.0  # first call loads the model: can be slow
    embedding_max_retries: int = 3            # extra attempts after a temporary failure


     # --- Database (PostgreSQL + pgvector) ---
    # SecretStr: the URL contains the password, so it must never appear in logs.
    database_url: SecretStr = SecretStr("")


        # --- RAG (Week 3) ---
    rag_top_k: int = 5                  # sources given to the model
    rag_min_score: float = 0.5          # below this best score, refuse without calling the LLM
    rag_max_context_tokens: int = 3000  # token budget for the sources

    # Tell pydantic-settings where the .env file is and how to read it.
    # extra="ignore": unknown variables in .env do not crash the app.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

        
    # --- Web UI (Week 3) ---
    # Origins allowed to call the API from a browser (CORS). Override with a JSON list in .env.
    cors_origins: list[str] = ["http://127.0.0.1:5173", "http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    """Return one cached Settings instance (a simple singleton)."""
    return Settings()