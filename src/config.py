"""Application configuration via pydantic-settings (reads from .env)."""

from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── LLM ───────────────────────────────────────────────────────────────────
    llm_provider: str = "gemini"
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    llm_model: str = "gemini-2.0-flash"
    llm_max_tokens: int = 700
    llm_temperature: float = 0.2
    use_llm: bool = True
    llm_timeout_seconds: float = 8.0

    # ── Service ───────────────────────────────────────────────────────────────
    service_port: int = 8000
    service_env: str = "development"
    log_level: str = "INFO"

    # ── Catalog ───────────────────────────────────────────────────────────────
    catalog_path: str = "data/catalog.json"
    catalog_refresh_interval: int = 86400  # seconds


    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
    )


settings = Settings()
