"""Typed environment-based settings for the API and local RAG pipeline."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Lenny Growth Assistant"
    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/lenny_growth"

    llm_provider: str = "ollama"
    agent_runtime: str = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"
    llm_timeout_seconds: float = 60.0
    llm_num_predict: int = 384
    llm_essay_num_predict: int = 2500
    llm_essay_num_ctx: int = 8192
    ollama_keep_alive: str = "10m"
    cloud_llm_api_key: str | None = None
    cloud_llm_model: str | None = None

    embedding_provider: str = "ollama"
    embedding_model: str = "nomic-embed-text"
    embedding_dimensions: int = 768
    embedding_batch_size: int = 16
    transcript_dir: str = "data-source/episodes"

    retrieval_top_k: int = 5
    chunk_size: int = 900
    chunk_overlap: int = 120

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings; clear the cache in tests after env changes."""
    return Settings()
