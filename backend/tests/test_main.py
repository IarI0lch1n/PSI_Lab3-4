"""Tests for FastAPI application construction."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config.settings import Settings
from app.main import app, create_app


def test_module_app_and_factory_preserve_application_metadata() -> None:
    application = create_app()

    assert isinstance(app, FastAPI)
    assert isinstance(application, FastAPI)
    assert app.title == application.title == "CurrencyHub API"
    assert application.description
    assert application.version == "0.1.0"


def test_root_endpoint_remains_available() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to CurrencyHub API"}


def test_application_creation_adds_current_rates_and_health_routes() -> None:
    application = create_app()
    paths = set(application.openapi()["paths"])

    assert paths == {
        "/",
        "/api/v1/currencies",
        "/api/v1/rates/latest",
        "/api/v1/health",
    }


def test_configured_origin_is_allowed_by_cors() -> None:
    settings = Settings(cors_allowed_origins=["https://client.example"])
    with TestClient(create_app(settings)) as client:
        response = client.options(
            "/",
            headers={
                "Origin": "https://client.example",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "content-type",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://client.example"
    assert "access-control-allow-credentials" not in response.headers


def test_unconfigured_origin_is_not_allowed_by_cors() -> None:
    settings = Settings(cors_allowed_origins=["https://client.example"])
    with TestClient(create_app(settings)) as client:
        response = client.options(
            "/",
            headers={
                "Origin": "https://untrusted.example",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert "access-control-allow-origin" not in response.headers
