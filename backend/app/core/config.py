from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_JWT_SECRET = "dev-only-insecure-secret-change-me-in-production"


class Settings(BaseSettings):
    """App settings, read from environment variables (and backend/.env in local dev)."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"
    database_url: str = "postgresql+psycopg://scraper:scraper@localhost:5432/smart_web_scraper"
    cors_origins: str = "http://localhost:3000"

    # Auth
    jwt_secret_key: str = DEV_JWT_SECRET
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # LLM extraction (Groq, OpenAI-compatible API)
    groq_api_key: str = ""
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_model: str = "openai/gpt-oss-120b"
    groq_fallback_model: str = "llama-3.3-70b-versatile"
    llm_timeout_seconds: float = 60.0
    max_page_chars: int = 24_000

    # Scraping
    fetch_timeout_seconds: float = 15.0
    max_page_bytes: int = 5_000_000
    playwright_enabled: bool = True
    browser_executable_path: str | None = None  # only needed if Chromium isn't where Playwright expects
    min_text_chars_before_render: int = 400

    # Background worker and limits
    worker_enabled: bool = True
    worker_poll_seconds: float = 2.0
    job_max_attempts: int = 3
    job_stale_after_seconds: int = 300
    jobs_per_hour: int = 30
    max_active_jobs_per_user: int = 5

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip().rstrip("/") for o in self.cors_origins.split(",") if o.strip()]

    @model_validator(mode="after")
    def _require_real_secret_in_production(self) -> "Settings":
        if self.environment == "production" and self.jwt_secret_key == DEV_JWT_SECRET:
            raise ValueError("Set JWT_SECRET_KEY to a long random value in production.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()