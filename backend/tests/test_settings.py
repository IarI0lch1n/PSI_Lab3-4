"""Unit tests for settings, CORS parsing, and structured logging."""

import logging
from app.core.config.settings import Settings
from app.core.logging.logger import StructuredFormatter, configure_logging, get_logger


def test_default_settings_loaded() -> None:
    """Verify that default settings load with expected values."""
    settings = Settings()
    assert settings.environment == "development"
    assert settings.debug is True
    assert settings.app_port == 8000
    assert settings.log_level == "INFO"
    assert "http://localhost:4200" in settings.cors_allowed_origins
    assert "http://127.0.0.1:4200" in settings.cors_allowed_origins
    assert settings.db_server == "localhost"
    assert settings.bnm_max_retries == 3
    assert settings.coingecko_max_retries == 3


def test_cors_origins_parsing() -> None:
    """Verify parsing of comma-separated and JSON list CORS origins."""
    # Comma-separated string
    s1 = Settings(cors_allowed_origins="http://localhost:3000, http://example.com")
    assert s1.cors_allowed_origins == ["http://localhost:3000", "http://example.com"]

    # JSON formatted list string
    s2 = Settings(cors_allowed_origins='["http://app.local", "http://api.local"]')
    assert s2.cors_allowed_origins == ["http://app.local", "http://api.local"]

    # List of strings
    s3 = Settings(cors_allowed_origins=["http://flutter.local"])
    assert s3.cors_allowed_origins == ["http://flutter.local"]

    # Empty string
    s4 = Settings(cors_allowed_origins="")
    assert s4.cors_allowed_origins == []


def test_log_level_normalization() -> None:
    """Verify log_level is normalized to uppercase."""
    settings = Settings(log_level="debug")
    assert settings.log_level == "DEBUG"


def test_structured_logger_configuration() -> None:
    """Verify logger creation and structured formatting."""
    settings = Settings(log_level="DEBUG")
    configure_logging(settings=settings)

    logger = get_logger("currencyhub.test")
    assert logger is not None
    assert logging.getLogger().level == logging.DEBUG

    # Test formatter outputs structured fields
    formatter = StructuredFormatter(json_format=False)
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test_path.py",
        lineno=10,
        msg="Test message",
        args=(),
        exc_info=None,
    )
    record.request_id = "req-12345"
    formatted = formatter.format(record)
    assert "Test message" in formatted
    assert "request_id=req-12345" in formatted
    assert "[INFO ]" in formatted


def test_json_logger_formatter() -> None:
    """Verify JSON formatting output."""
    formatter = StructuredFormatter(json_format=True)
    record = logging.LogRecord(
        name="test_logger",
        level=logging.WARNING,
        pathname="test_path.py",
        lineno=20,
        msg="Warning message",
        args=(),
        exc_info=None,
    )
    record.user_id = 42
    formatted = formatter.format(record)
    assert '"level": "WARNING"' in formatted
    assert '"message": "Warning message"' in formatted
    assert '"user_id": 42' in formatted


def test_env_variable_overrides(monkeypatch) -> None:
    """Verify environment variables override defaults."""
    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.setenv("LOG_LEVEL", "debug")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://app.currencyhub.local, https://admin.currencyhub.local")
    monkeypatch.setenv("DATABASE_URL", "mssql+pyodbc://custom_db")

    settings = Settings()
    assert settings.environment == "staging"
    assert settings.log_level == "DEBUG"
    assert settings.cors_allowed_origins == [
        "https://app.currencyhub.local",
        "https://admin.currencyhub.local",
    ]
    assert settings.database_url == "mssql+pyodbc://custom_db"

