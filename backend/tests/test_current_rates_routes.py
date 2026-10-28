"""Focused API tests for supported currencies and latest rates."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_latest_snapshot_use_case,
    get_list_currencies_use_case,
)
from app.application.use_cases.get_latest_snapshot import (
    LatestSnapshotUnavailableError,
)
from app.core.config.settings import Settings
from app.domain.entities.currency import Currency
from app.domain.entities.rate_entry import RateEntry
from app.domain.entities.rate_snapshot import RateSnapshot
from app.domain.enums.currency_type import CurrencyType
from app.domain.enums.freshness_state import FreshnessState
from app.main import create_app


_SNAPSHOT_ID = UUID("00000000-0000-0000-0000-000000000301")
_CAPTURED_AT = datetime(2026, 10, 28, 12, 0, tzinfo=UTC)
_FIAT_EFFECTIVE_AT = datetime(2026, 10, 28, 9, 0, tzinfo=UTC)
_CRYPTO_EFFECTIVE_AT = datetime(2026, 10, 28, 11, 45, tzinfo=UTC)


class FakeListCurrencies:
    def __init__(self, currencies: tuple[Currency, ...]) -> None:
        self.currencies = currencies

    def execute(self) -> tuple[Currency, ...]:
        return self.currencies


class FakeGetLatestSnapshot:
    def __init__(
        self,
        snapshot: RateSnapshot | None = None,
        error: Exception | None = None,
    ) -> None:
        self.snapshot = snapshot
        self.error = error

    def execute(self) -> RateSnapshot:
        if self.error is not None:
            raise self.error
        assert self.snapshot is not None
        return self.snapshot


def _snapshot() -> RateSnapshot:
    return RateSnapshot(
        _SNAPSHOT_ID,
        _CAPTURED_AT,
        (
            RateEntry(
                snapshot_id=_SNAPSHOT_ID,
                entry_id=UUID("00000000-0000-0000-0000-000000000311"),
                currency="RON",
                normalized_rate_to_mdl=Decimal("3.912345678901234567"),
                nominal_unit=100,
                provider_name="BNM",
                provider_type=CurrencyType.FIAT,
                effective_at=_FIAT_EFFECTIVE_AT,
                freshness_state=FreshnessState.FALLBACK,
                is_fallback=True,
                is_stale=False,
            ),
            RateEntry(
                snapshot_id=_SNAPSHOT_ID,
                entry_id=UUID("00000000-0000-0000-0000-000000000312"),
                currency="BTC",
                normalized_rate_to_mdl=Decimal("542240.10"),
                nominal_unit=1,
                provider_name="CoinGecko",
                provider_type=CurrencyType.CRYPTO,
                effective_at=_CRYPTO_EFFECTIVE_AT,
                freshness_state=FreshnessState.CACHED,
                is_fallback=False,
                is_stale=True,
            ),
        ),
    )


def _client(
    *,
    currencies: tuple[Currency, ...] = (),
    snapshot: RateSnapshot | None = None,
    snapshot_error: Exception | None = None,
) -> TestClient:
    application = create_app(Settings())
    application.dependency_overrides[get_list_currencies_use_case] = lambda: (
        FakeListCurrencies(currencies)
    )
    application.dependency_overrides[get_latest_snapshot_use_case] = lambda: (
        FakeGetLatestSnapshot(snapshot, snapshot_error)
    )
    return TestClient(application)


def test_currencies_endpoint_returns_supported_currency_metadata_in_order() -> None:
    currencies = (
        Currency(code="BTC", type=CurrencyType.CRYPTO),
        Currency(code="USD", type=CurrencyType.FIAT),
    )
    with _client(currencies=currencies) as client:
        response = client.get("/api/v1/currencies")

    assert response.status_code == 200
    assert response.json() == {
        "currencies": [
            {
                "code": "BTC",
                "name": "Bitcoin",
                "type": "crypto",
                "is_supported": True,
            },
            {
                "code": "USD",
                "name": "US Dollar",
                "type": "fiat",
                "is_supported": True,
            },
        ]
    }


def test_latest_rates_endpoint_preserves_decimal_precision_and_entry_context() -> None:
    with _client(snapshot=_snapshot()) as client:
        response = client.get("/api/v1/rates/latest")

    assert response.status_code == 200
    payload = response.json()
    assert payload["snapshot_id"] == str(_SNAPSHOT_ID)
    assert payload["captured_at"] == "2026-10-28T12:00:00Z"
    assert "provider_name" not in payload
    assert "freshness_state" not in payload
    fiat, crypto = payload["rates"]
    assert fiat == {
        "currency": "RON",
        "normalized_rate_to_mdl": "3.912345678901234567",
        "nominal_unit": 100,
        "provider_name": "BNM",
        "provider_type": "fiat",
        "effective_at": "2026-10-28T09:00:00Z",
        "freshness_state": "fallback",
        "is_fallback": True,
        "is_stale": False,
    }
    assert crypto == {
        "currency": "BTC",
        "normalized_rate_to_mdl": "542240.10",
        "nominal_unit": 1,
        "provider_name": "CoinGecko",
        "provider_type": "crypto",
        "effective_at": "2026-10-28T11:45:00Z",
        "freshness_state": "cached",
        "is_fallback": False,
        "is_stale": True,
    }
    assert isinstance(fiat["normalized_rate_to_mdl"], str)
    assert isinstance(crypto["normalized_rate_to_mdl"], str)


def test_latest_rates_endpoint_maps_unavailable_snapshot_to_sanitized_503() -> None:
    error = LatestSnapshotUnavailableError()
    with _client(snapshot_error=error) as client:
        response = client.get("/api/v1/rates/latest")

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "snapshot_unavailable",
            "message": "A complete rate snapshot is currently unavailable.",
        }
    }


def test_current_rates_routes_are_mounted_only_at_api_v1_paths() -> None:
    paths = set(create_app().openapi()["paths"])

    assert "/api/v1/currencies" in paths
    assert "/api/v1/rates/latest" in paths
    assert "/api/v1/health" in paths
    assert "/currencies" not in paths
    assert "/rates/latest" not in paths
