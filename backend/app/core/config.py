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

    # Scraping
    fetch_timeout_seconds: float = 15.0
    max_page_bytes: int = 5_000_000
    playwright_enabled: bool = True
    browser_executable_path: str | None = None  # only needed if Chromium isn't where Playwright expects
    min_text_chars_before_render: int = 400

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