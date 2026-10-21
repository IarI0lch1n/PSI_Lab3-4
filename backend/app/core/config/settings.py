"""Application settings and environment configuration."""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_CURRENT_FILE = Path(__file__).resolve()
_BACKEND_DIR = _CURRENT_FILE.parents[3]
_PROJECT_ROOT = _BACKEND_DIR.parent


class Settings(BaseSettings):
    """CurrencyHub backend configuration backed by environment variables."""

    # Application Environment
    environment: str = "development"
    debug: bool = True
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"

    # Microsoft SQL Server Configuration
    database_url: str = (
        "mssql+pyodbc:///?odbc_connect=DRIVER={ODBC+Driver+18+for+SQL+Server};"
        "SERVER=localhost;DATABASE=currencyhub;Trusted_Connection=yes;"
        "TrustServerCertificate=yes"
    )
    db_server: str = "localhost"
    db_port: int = 1433
    db_name: str = "currencyhub"
    db_user: str = "placeholder_db_user"
    db_password: str = "placeholder_db_password"
    db_trust_server_certificate: bool = True

    # National Bank of Moldova (BNM) Provider Configuration
    bnm_base_url: str = "https://www.bnm.md/en/official_exchange_rates"
    bnm_timeout_seconds: float = 10.0
    bnm_max_retries: int = 3

    # CoinGecko-compatible Cryptocurrency Provider Configuration
    coingecko_base_url: str = "https://api.coingecko.com/api/v3"
    coingecko_api_key: str = "placeholder_coingecko_api_key"
    coingecko_timeout_seconds: float = 10.0
    coingecko_max_retries: int = 3

    # CORS Configuration
    # Typed as str | list[str] so pydantic-settings does not attempt json.loads on comma-separated env values
    cors_allowed_origins: str | list[str] = Field(
        default_factory=lambda: ["http://localhost:4200", "http://127.0.0.1:4200"]
    )

    @field_validator("cors_allowed_origins")
    @classmethod
    def parse_cors_allowed_origins(cls, value: Any) -> list[str]:
        """Parse CORS allowed origins into a list of origin strings."""
        if isinstance(value, str):
            val = value.strip()
            if not val:
                return []
            if val.startswith("[") and val.endswith("]"):
                try:
                    parsed = json.loads(val)
                    if isinstance(parsed, list):
                        return [str(item).strip() for item in parsed if str(item).strip()]
                except json.JSONDecodeError:
                    pass
            return [origin.strip() for origin in val.split(",") if origin.strip()]
        if isinstance(value, (list, tuple, set)):
            return [str(origin).strip() for origin in value if str(origin).strip()]
        return []

    @field_validator("log_level", mode="before")
    @classmethod
    def validate_log_level(cls, value: Any) -> str:
        """Normalize log level string to uppercase."""
        if isinstance(value, str):
            return value.strip().upper()
        return "INFO"

    model_config = SettingsConfigDict(
        env_file=(
            _BACKEND_DIR / ".env",
            _PROJECT_ROOT / ".env",
            ".env",
        ),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton instance of Settings."""
    return Settings()
