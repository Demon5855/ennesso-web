"""Application configuration loaded from environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # -----------------------------------------------------------------
    # Application
    # -----------------------------------------------------------------
    app_env: Literal["development", "staging", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # -----------------------------------------------------------------
    # Supabase
    # -----------------------------------------------------------------
    supabase_url: str
    supabase_service_role_key: str

    # -----------------------------------------------------------------
    # External data sources
    # -----------------------------------------------------------------
    cenace_ckan_base_url: AnyHttpUrl = AnyHttpUrl(
        "https://datosabiertos.cenace.gob.ec/api"
    )
    cenace_xhr_base_url: AnyHttpUrl = AnyHttpUrl(
        "https://www.cenace.gob.ec/SiSEWeb"
    )
    cenace_generation_resource_id: str = ""
    arcernnr_base_url: AnyHttpUrl = AnyHttpUrl(
        "https://www.regulacionelectrica.gob.ec"
    )

    # -----------------------------------------------------------------
    # AI
    # -----------------------------------------------------------------
    anthropic_api_key: str = ""

    # -----------------------------------------------------------------
    # Payments
    # -----------------------------------------------------------------
    lemonsqueezy_webhook_secret: str = ""

    # -----------------------------------------------------------------
    # CORS
    # -----------------------------------------------------------------
    cors_origins: list[str] = ["http://localhost:3000"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",")]
        return value

    # -----------------------------------------------------------------
    # Scheduler
    # -----------------------------------------------------------------
    scheduler_ingestion_cron: str = "0 */1 * * *"  # every hour


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings: Settings = get_settings()
