"""Contract tests for supported currencies and latest-rate API responses."""

from datetime import UTC, datetime, timedelta, timezone
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
from app.domain.entities.currency import (
    SUPPORTED_CRYPTO_CURRENCIES,
    SUPPORTED_FIAT_CURRENCIES,
    Currency,
)
from app.domain.entities.rate_entry import RateEntry
from app.domain.entities.rate_snapshot import RateSnapshot
from app.domain.enums.currency_type import CurrencyType
from app.domain.enums.freshness_state import FreshnessState
from app.main import create_app


_SNAPSHOT_ID = UUID("00000000-0000-0000-0000-000000000501")
_CAPTURED_AT = datetime(2026, 10, 28, 12, 0, tzinfo=UTC)
_FIAT_EFFECTIVE_AT = datetime(
    2026,
    10,
    27,
    tzinfo=timezone(timedelta(hours=2)),
)
_CRYPTO_EFFECTIVE_AT = datetime(2026, 10, 28, 11, 52, tzinfo=UTC)
_CANONICAL_FIAT_CODES = (
    "MDL",
    "USD",
    "EUR",
    "RUB",
    "CNY",
    "GBP",
    "RON",
    "UAH",
    "CHF",
    "JPY",
)
_CANONICAL_CRYPTO_CODES = (
    "BTC",
    "ETH",
    "SOL",
    "BNB",
    "XRP",
    "ADA",
    "DOGE",
    "USDT",
)


class FakeListCurrencies:
    def __init__(self, currencies: tuple[Currency, ...]) -> None:
        self._currencies = currencies

    def execute(self) -> tuple[Currency, ...]:
        return self._currencies


class FakeGetLatestSnapshot:
    def __init__(
        self,
        snapshot: RateSnapshot | None = None,
        *,
        unavailable: bool = False,
    ) -> None:
        self._snapshot = snapshot
        self._unavailable = unavailable

    def execute(self) -> RateSnapshot:
        if self._unavailable:
            raise LatestSnapshotUnavailableError()
        assert self._snapshot is not None
        return self._snapshot


def _all_supported_currencies() -> tuple[Currency, ...]:
    return (
        *(
            Currency(code=code, name=name, type=CurrencyType.FIAT)
            for code, name in SUPPORTED_FIAT_CURRENCIES.items()
        ),
        *(
            Currency(code=code, name=name, type=CurrencyType.CRYPTO)
            for code, name in SUPPORTED_CRYPTO_CURRENCIES.items()
        ),
    )


def _snapshot() -> RateSnapshot:
    rates = (
        RateEntry(
            snapshot_id=_SNAPSHOT_ID,
            entry_id=UUID("00000000-0000-0000-0000-000000000511"),
            currency="USD",
            normalized_rate_to_mdl=Decimal("17.400000000000000001"),
            nominal_unit=1,
            provider_name="BNM",
            provider_type=CurrencyType.FIAT,
            effective_at=datetime(2026, 10, 28, 10, 0, tzinfo=UTC),
            freshness_state=FreshnessState.LIVE,
            is_fallback=False,
            is_stale=False,
        ),
        RateEntry(
            snapshot_id=_SNAPSHOT_ID,
            entry_id=UUID("00000000-0000-0000-0000-000000000512"),
            currency="RON",
            normalized_rate_to_mdl=(
                Decimal("391.2345678901234567") / Decimal("100")
            ),
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
            entry_id=UUID("00000000-0000-0000-0000-000000000513"),
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
    )
    return RateSnapshot(_SNAPSHOT_ID, _CAPTURED_AT, rates)


def _client(
    *,
    snapshot: RateSnapshot | None = None,
    snapshot_unavailable: bool = False,
) -> TestClient:
    application = create_app(Settings())
    application.dependency_overrides[get_list_currencies_use_case] = lambda: (
        FakeListCurrencies(_all_supported_currencies())
    )
    application.dependency_overrides[get_latest_snapshot_use_case] = lambda: (
        FakeGetLatestSnapshot(snapshot, unavailable=snapshot_unavailable)
    )
    return TestClient(application, raise_server_exceptions=False)


def test_currencies_contract_contains_exact_supported_set_and_metadata() -> None:
    with _client() as client:
        response = client.get("/api/v1/currencies")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"currencies"}
    currencies = payload["currencies"]
    assert len(currencies) == 18
    assert [item["code"] for item in currencies[:10]] == list(
        _CANONICAL_FIAT_CODES
    )
    assert [item["code"] for item in currencies[10:]] == list(
        _CANONICAL_CRYPTO_CODES
    )
    assert len([item for item in currencies if item["type"] == "fiat"]) == 10
    assert len([item for item in currencies if item["type"] == "crypto"]) == 8
    for item in currencies:
        assert set(item) == {"code", "name", "type", "is_supported"}
        assert item["type"] in {"fiat", "crypto"}
        assert item["is_supported"] is True
        assert "provider_name" not in item
        assert "normalized_rate_to_mdl" not in item


def test_latest_rates_contract_preserves_snapshot_and_all_entry_metadata() -> None:
    with _client(snapshot=_snapshot()) as client:
        response = client.get("/api/v1/rates/latest")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"snapshot_id", "captured_at", "rates"}
    assert payload["snapshot_id"] == str(_SNAPSHOT_ID)
    assert payload["captured_at"] == "2026-10-28T12:00:00Z"
    assert "provider_name" not in payload
    assert "provider_type" not in payload
    assert "effective_at" not in payload
    assert "freshness_state" not in payload
    assert "is_fallback" not in payload
    assert "is_stale" not in payload

    expected_fields = {
        "currency",
        "normalized_rate_to_mdl",
        "nominal_unit",
        "provider_name",
        "provider_type",
        "effective_at",
        "freshness_state",
        "is_fallback",
        "is_stale",
    }
    rates = payload["rates"]
    assert [rate["currency"] for rate in rates] == ["USD", "RON", "BTC"]
    assert all(set(rate) == expected_fields for rate in rates)

    usd, ron, btc = rates
    assert usd["normalized_rate_to_mdl"] == "17.400000000000000001"
    assert isinstance(usd["normalized_rate_to_mdl"], str)
    assert usd["provider_name"] == "BNM"
    assert usd["provider_type"] == "fiat"
    assert usd["freshness_state"] == "live"
    assert usd["is_fallback"] is False
    assert usd["is_stale"] is False

    assert ron["normalized_rate_to_mdl"] == "3.912345678901234567"
    assert ron["nominal_unit"] == 100
    assert ron["provider_name"] == "BNM"
    assert ron["provider_type"] == "fiat"
    assert ron["effective_at"] == "2026-10-27T00:00:00+02:00"
    assert ron["freshness_state"] == "fallback"
    assert ron["is_fallback"] is True
    assert ron["is_stale"] is False

    assert btc["normalized_rate_to_mdl"] == "542240.10"
    assert btc["provider_name"] == "CoinGecko"
    assert btc["provider_type"] == "crypto"
    assert btc["effective_at"] == "2026-10-28T11:52:00Z"
    assert btc["freshness_state"] == "cached"
    assert btc["is_fallback"] is False
    assert btc["is_stale"] is True

    assert {rate["freshness_state"] for rate in rates} == {
        "live",
        "fallback",
        "cached",
    }
    assert "stale" not in {rate["freshness_state"] for rate in rates}
    assert all(rate["effective_at"] != payload["captured_at"] for rate in rates)


def test_latest_rates_contract_documents_public_response_fields_in_openapi() -> None:
    application = create_app()
    openapi = application.openapi()
    response_schema = openapi["paths"]["/api/v1/rates/latest"]["get"][
        "responses"
    ]["200"]["content"]["application/json"]["schema"]
    snapshot_schema = openapi["components"]["schemas"][
        response_schema["$ref"].rsplit("/", 1)[-1]
    ]
    entry_ref = snapshot_schema["properties"]["rates"]["items"]["$ref"]
    entry_schema = openapi["components"]["schemas"][
        entry_ref.rsplit("/", 1)[-1]
    ]

    assert entry_schema["properties"]["normalized_rate_to_mdl"]["type"] == "string"
    assert {
        "freshness_state",
        "is_fallback",
        "is_stale",
    }.issubset(entry_schema["properties"])
    freshness_ref = entry_schema["properties"]["freshness_state"]["$ref"]
    freshness_schema = openapi["components"]["schemas"][
        freshness_ref.rsplit("/", 1)[-1]
    ]
    assert freshness_schema["enum"] == ["live", "fallback", "cached"]


def test_latest_rates_contract_returns_sanitized_503_when_snapshot_unavailable() -> None:
    with _client(snapshot_unavailable=True) as client:
        response = client.get("/api/v1/rates/latest")

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "snapshot_unavailable",
            "message": "A complete rate snapshot is currently unavailable.",
        }
    }
