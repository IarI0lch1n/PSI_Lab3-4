"""Tests for sanitized common API exception responses."""

from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.application.services.snapshot_service import SnapshotAssemblyError
from app.core.config.settings import Settings
from app.infrastructure.providers.bnm_rate_provider import BnmRateProviderError
from app.infrastructure.providers.coingecko_rate_provider import (
    CoinGeckoRateProviderError,
)
from app.main import create_app


def _client_for_exception(path: str, exception: Exception) -> TestClient:
    application = create_app(Settings())

    @application.get(path)
    def raise_error():
        raise exception

    return TestClient(application, raise_server_exceptions=False)


def test_snapshot_assembly_error_maps_to_sanitized_503() -> None:
    with _client_for_exception(
        "/test-snapshot-error",
        SnapshotAssemblyError("missing USD"),
    ) as client:
        response = client.get("/test-snapshot-error")

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "snapshot_unavailable",
            "message": "A complete rate snapshot is currently unavailable.",
        }
    }


def test_provider_errors_map_to_sanitized_502_without_secrets() -> None:
    for path, error_type in (
        ("/test-bnm-error", BnmRateProviderError),
        ("/test-coingecko-error", CoinGeckoRateProviderError),
    ):
        secret = "api-key-secret"
        with _client_for_exception(path, error_type(secret)) as client:
            response = client.get(path)

        assert response.status_code == 502
        assert response.json() == {
            "error": {
                "code": "provider_unavailable",
                "message": "A rate provider is currently unavailable.",
            }
        }
        assert secret not in response.text


def test_database_error_maps_to_sanitized_503_without_connection_details() -> None:
    secret = "password=do-not-expose"
    with _client_for_exception(
        "/test-database-error",
        SQLAlchemyError(secret),
    ) as client:
        response = client.get("/test-database-error")

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "database_unavailable",
            "message": "The database service is currently unavailable.",
        }
    }
    assert secret not in response.text


def test_unexpected_error_maps_to_sanitized_500() -> None:
    secret = "internal traceback secret"
    with _client_for_exception(
        "/test-unexpected-error",
        RuntimeError(secret),
    ) as client:
        response = client.get("/test-unexpected-error")

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "internal_error",
            "message": "An unexpected internal error occurred.",
        }
    }
    assert secret not in response.text
