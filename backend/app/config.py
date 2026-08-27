from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    anthropic_api_key: str = Field(default="", repr=False)
    claude_model: str = "claude-sonnet-4-5-20250929"
    frontend_origins: str = "http://localhost:5173"
    database_url: str = "postgresql+psycopg://jobpilot:jobpilot@localhost:5433/jobpilot"
    max_upload_bytes: int = 10 * 1024 * 1024
    job_fetch_timeout_seconds: float = 10.0
    job_fetch_max_bytes: int = 2 * 1024 * 1024
    job_fetch_max_redirects: int = 3
    job_import_page_size: int = 100
    job_import_max_jobs: int = 2_000
    job_import_max_pages: int = 50
    job_import_timeout_seconds: float = 20.0
    job_import_max_response_bytes: int = 5 * 1024 * 1024
    job_import_page_delay_seconds: float = 0.35
    job_import_max_retries: int = 3
    discovery_ttl_minutes: int = 60
    discovery_max_sessions: int = 20
    discovery_max_results: int = 500
    app_timezone: str = "Australia/Sydney"

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
