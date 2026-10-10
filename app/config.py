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

    # Tell pydantic-settings where the .env file is and how to read it.
    # extra="ignore": unknown variables in .env do not crash the app.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return one cached Settings instance (a simple singleton)."""
    return Settings()