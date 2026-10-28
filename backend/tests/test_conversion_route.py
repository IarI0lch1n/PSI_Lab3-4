"""Focused API wiring tests for the T030 conversion endpoint."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api import dependencies
from app.api.dependencies import get_convert_currency_use_case
from app.application.use_cases.convert_currency import (
    ConversionRateUnavailableError,
    ConversionSnapshotUnavailableError,
    ConvertCurrency,
    InvalidConversionInputError,
)
from app.core.config.settings import Settings
from app.domain.entities.rate_entry import RateEntry
from app.domain.entities.rate_snapshot import RateSnapshot
from app.domain.enums.currency_type import CurrencyType
from app.domain.enums.freshness_state import FreshnessState
from app.main import create_app


_SNAPSHOT_ID = UUID("00000000-0000-0000-0000-000000000401")
_CAPTURED_AT = datetime(2026, 10, 28, 12, 0, tzinfo=UTC)
_USD_EFFECTIVE_AT = datetime(2026, 10, 28, 9, 0, tzinfo=UTC)
_BTC_EFFECTIVE_AT = datetime(2026, 10, 28, 11, 45, tzinfo=UTC)


class StubConvertCurrency:
    def __init__(
        self,
        *,
        snapshot: RateSnapshot | None = None,
        error: Exception | None = None,
    ) -> None:
        self._use_case = ConvertCurrency(_StubUnitOfWork(snapshot))
        self.error = error

    def execute(
        self,
        amount: Decimal | str | int,
        source_currency: str,
        target_currency: str,
    ):
        if self.error is not None:
            raise self.error
        return self._use_case.execute(amount, source_currency, target_currency)


class _StubRateRepository:
    def __init__(self, snapshot: RateSnapshot | None) -> None:
        self.snapshot = snapshot

    def get_latest_usable_snapshot(self) -> RateSnapshot | None:
        return self.snapshot


class _StubUnitOfWork:
    def __init__(self, snapshot: RateSnapshot | None) -> None:
        self.rate_repository = _StubRateRepository(snapshot)
        self.enter_count = 0

    def __enter__(self) -> "_StubUnitOfWork":
        self.enter_count += 1
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        return None

    def commit(self) -> None:
        raise AssertionError("Conversion use case must not commit.")


def _snapshot() -> RateSnapshot:
    return RateSnapshot(
        _SNAPSHOT_ID,
        _CAPTURED_AT,
        (
            RateEntry(
                snapshot_id=_SNAPSHOT_ID,
                entry_id=UUID("00000000-0000-0000-0000-000000000411"),
                currency="USD",
                normalized_rate_to_mdl=Decimal("17.400000000000000001"),
                provider_name="BNM",
                provider_type=CurrencyType.FIAT,
                effective_at=_USD_EFFECTIVE_AT,
                freshness_state=FreshnessState.FALLBACK,
                is_fallback=True,
                is_stale=False,
            ),
            RateEntry(
                snapshot_id=_SNAPSHOT_ID,
                entry_id=UUID("00000000-0000-0000-0000-000000000412"),
                currency="BTC",
                normalized_rate_to_mdl=Decimal(
                    "542240.123456789012345678"
                ),
                provider_name="CoinGecko",
                provider_type=CurrencyType.CRYPTO,
                effective_at=_BTC_EFFECTIVE_AT,
                freshness_state=FreshnessState.CACHED,
                is_fallback=False,
                is_stale=True,
            ),
        ),
    )


def _client(
    *,
    snapshot: RateSnapshot | None = None,
    error: Exception | None = None,
) -> TestClient:
    application = create_app(Settings())
    application.dependency_overrides[get_convert_currency_use_case] = lambda: (
        StubConvertCurrency(snapshot=snapshot, error=error)
    )
    return TestClient(application, raise_server_exceptions=False)


def test_conversion_route_preserves_exact_decimal_strings_and_both_rate_legs() -> None:
    with _client(snapshot=_snapshot()) as client:
        response = client.post(
            "/api/v1/convert",
            json={
                "amount": "123.456789012345678901",
                "source_currency": "USD",
                "target_currency": "BTC",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source_amount"] == "123.456789012345678901"
    assert isinstance(payload["source_amount"], str)
    assert isinstance(payload["converted_amount"], str)
    assert isinstance(payload["rate_value"], str)
    assert payload["source_currency"] == "USD"
    assert payload["target_currency"] == "BTC"
    assert "provider_name" not in payload
    assert "freshness_state" not in payload
    assert payload["rate_context"] == {
        "source_rate": {
            "currency": "USD",
            "provider_name": "BNM",
            "effective_at": "2026-10-28T09:00:00Z",
            "freshness_state": "fallback",
            "is_fallback": True,
            "is_stale": False,
        },
        "target_rate": {
            "currency": "BTC",
            "provider_name": "CoinGecko",
            "effective_at": "2026-10-28T11:45:00Z",
            "freshness_state": "cached",
            "is_fallback": False,
            "is_stale": True,
        },
        "snapshot_id": str(_SNAPSHOT_ID),
    }


def test_same_currency_response_preserves_amount_and_single_rate_context() -> None:
    with _client(snapshot=_snapshot()) as client:
        response = client.post(
            "/api/v1/convert",
            json={
                "amount": "123.4500",
                "source_currency": "USD",
                "target_currency": "USD",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source_amount"] == "123.4500"
    assert payload["converted_amount"] == "123.4500"
    assert payload["rate_value"] == "1"
    assert payload["rate_context"]["source_rate"] == payload["rate_context"][
        "target_rate"
    ]


@pytest.mark.parametrize(
    ("error", "status_code", "code", "message"),
    [
        (
            InvalidConversionInputError("unsafe detail"),
            422,
            "invalid_conversion_input",
            "Amount and currencies must be valid and supported.",
        ),
        (
            ConversionSnapshotUnavailableError(),
            503,
            "conversion_unavailable",
            "Conversion is currently unavailable.",
        ),
        (
            ConversionRateUnavailableError("ETH"),
            422,
            "rate_unavailable",
            "No usable rate is available for ETH.",
        ),
    ],
)
def test_conversion_errors_use_sanitized_error_envelope(
    error: Exception,
    status_code: int,
    code: str,
    message: str,
) -> None:
    with _client(error=error) as client:
        response = client.post(
            "/api/v1/convert",
            json={
                "amount": "1",
                "source_currency": "USD",
                "target_currency": "BTC",
            },
        )

    assert response.status_code == status_code
    assert response.json() == {"error": {"code": code, "message": message}}
    assert "unsafe detail" not in response.text


def test_conversion_request_requires_string_amount_and_exact_fields() -> None:
    with _client(snapshot=_snapshot()) as client:
        numeric_amount = client.post(
            "/api/v1/convert",
            json={
                "amount": 1.25,
                "source_currency": "USD",
                "target_currency": "BTC",
            },
        )
        extra_field = client.post(
            "/api/v1/convert",
            json={
                "amount": "1.25",
                "source_currency": "USD",
                "target_currency": "BTC",
                "unexpected": True,
            },
        )

    assert numeric_amount.status_code == 422
    assert extra_field.status_code == 422


def test_conversion_openapi_documents_request_response_and_provenance_fields() -> None:
    openapi = create_app().openapi()
    operation = openapi["paths"]["/api/v1/convert"]["post"]
    request_ref = operation["requestBody"]["content"]["application/json"]["schema"][
        "$ref"
    ]
    response_ref = operation["responses"]["200"]["content"]["application/json"][
        "schema"
    ]["$ref"]
    schemas = openapi["components"]["schemas"]
    request_schema = schemas[request_ref.rsplit("/", 1)[-1]]
    response_schema = schemas[response_ref.rsplit("/", 1)[-1]]

    assert set(request_schema["properties"]) == {
        "amount",
        "source_currency",
        "target_currency",
    }
    assert request_schema["properties"]["amount"]["type"] == "string"
    assert set(response_schema["properties"]) == {
        "source_amount",
        "converted_amount",
        "source_currency",
        "target_currency",
        "rate_value",
        "rate_context",
    }
    for field in ("source_amount", "converted_amount", "rate_value"):
        assert response_schema["properties"][field]["type"] == "string"

    context_ref = response_schema["properties"]["rate_context"]["$ref"]
    context_schema = schemas[context_ref.rsplit("/", 1)[-1]]
    leg_ref = context_schema["properties"]["source_rate"]["$ref"]
    leg_schema = schemas[leg_ref.rsplit("/", 1)[-1]]
    assert set(leg_schema["properties"]) == {
        "currency",
        "provider_name",
        "effective_at",
        "freshness_state",
        "is_fallback",
        "is_stale",
    }
    assert leg_schema["properties"]["freshness_state"]["$ref"].endswith(
        "/FreshnessState"
    )
    freshness_schema = schemas["FreshnessState"]
    assert set(freshness_schema["enum"]) == {"live", "fallback", "cached"}


def test_conversion_dependency_constructs_an_unentered_unit_of_work(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    unit_of_work = _StubUnitOfWork(_snapshot())
    monkeypatch.setattr(
        dependencies,
        "_create_unit_of_work",
        lambda settings: unit_of_work,
    )

    use_case = get_convert_currency_use_case(Settings())

    assert isinstance(use_case, ConvertCurrency)
    assert use_case._unit_of_work is unit_of_work
    assert unit_of_work.rate_repository.snapshot is not None
    assert unit_of_work.enter_count == 0
