"""Contract tests for the public currency-conversion API."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import NAMESPACE_OID, UUID, uuid5

import pytest
from fastapi.testclient import TestClient

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

SNAPSHOT_ID = UUID("00000000-0000-0000-0000-000000000601")
CAPTURED_AT = datetime(2026, 10, 28, 12, 0, tzinfo=UTC)
FIAT_EFFECTIVE_AT = datetime(2026, 10, 27, 9, 0, tzinfo=UTC)
CRYPTO_EFFECTIVE_AT = datetime(2026, 10, 28, 11, 45, tzinfo=UTC)
AMOUNT = "123.456789012345678901"


class FakeRateRepository:
    def __init__(self, snapshot: RateSnapshot | None) -> None:
        self.snapshot = snapshot

    def get_latest_usable_snapshot(self) -> RateSnapshot | None:
        return self.snapshot


class FakeUnitOfWork:
    def __init__(self, snapshot: RateSnapshot | None) -> None:
        self.rate_repository = FakeRateRepository(snapshot)

    def __enter__(self) -> "FakeUnitOfWork":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        return None

    def commit(self) -> None:
        raise AssertionError("A conversion request must not commit.")


def _rate(
    currency: str,
    normalized_rate: str,
    provider_name: str,
    provider_type: CurrencyType,
    effective_at: datetime,
    freshness_state: FreshnessState = FreshnessState.LIVE,
    *,
    is_fallback: bool = False,
    is_stale: bool = False,
) -> RateEntry:
    return RateEntry(
        snapshot_id=SNAPSHOT_ID,
        entry_id=uuid5(NAMESPACE_OID, f"{SNAPSHOT_ID}:{currency}"),
        currency=currency,
        normalized_rate_to_mdl=Decimal(normalized_rate),
        provider_name=provider_name,
        provider_type=provider_type,
        effective_at=effective_at,
        freshness_state=freshness_state,
        is_fallback=is_fallback,
        is_stale=is_stale,
    )


def _snapshot(
    rates: tuple[RateEntry, ...] | None = None,
) -> RateSnapshot:
    return RateSnapshot(
        SNAPSHOT_ID,
        CAPTURED_AT,
        rates
        if rates is not None
        else (
            _rate(
                "EUR",
                "20.176000000000000001",
                "BNM",
                CurrencyType.FIAT,
                FIAT_EFFECTIVE_AT,
                FreshnessState.FALLBACK,
                is_fallback=True,
            ),
            _rate(
                "USD",
                "17.400000000000000001",
                "BNM",
                CurrencyType.FIAT,
                FIAT_EFFECTIVE_AT,
            ),
            _rate(
                "BTC",
                "1465834.123456789012345678",
                "CoinGecko",
                CurrencyType.CRYPTO,
                CRYPTO_EFFECTIVE_AT,
                FreshnessState.CACHED,
                is_stale=True,
            ),
            _rate(
                "ETH",
                "75000.250000000000000001",
                "CoinGecko",
                CurrencyType.CRYPTO,
                CRYPTO_EFFECTIVE_AT,
            ),
        ),
    )


def _client(
    snapshot: RateSnapshot | None = None,
    *,
    use_case_error: Exception | None = None,
) -> TestClient:
    application = create_app(Settings())

    def provide_conversion_use_case() -> ConvertCurrency:
        if use_case_error is not None:
            class RaisingConversionUseCase:
                def execute(self, amount, source_currency, target_currency):
                    raise use_case_error

            return RaisingConversionUseCase()  # type: ignore[return-value]
        return ConvertCurrency(FakeUnitOfWork(snapshot))

    application.dependency_overrides[get_convert_currency_use_case] = (
        provide_conversion_use_case
    )
    return TestClient(application, raise_server_exceptions=False)


def _post(
    client: TestClient,
    amount: str = AMOUNT,
    source: str = "EUR",
    target: str = "BTC",
):
    return client.post(
        "/api/v1/convert",
        json={
            "amount": amount,
            "source_currency": source,
            "target_currency": target,
        },
    )


def test_conversion_response_has_exact_shape_decimal_strings_and_both_legs() -> None:
    snapshot = _snapshot()
    source_rate = snapshot.get_rate("EUR")
    target_rate = snapshot.get_rate("BTC")
    assert source_rate is not None
    assert target_rate is not None
    expected_rate = (
        source_rate.normalized_rate_to_mdl / target_rate.normalized_rate_to_mdl
    )
    expected_amount = Decimal(AMOUNT) * expected_rate

    with _client(snapshot) as client:
        response = _post(client)

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {
        "source_amount",
        "converted_amount",
        "source_currency",
        "target_currency",
        "rate_value",
        "rate_context",
    }
    assert payload["source_amount"] == AMOUNT
    assert payload["converted_amount"] == format(expected_amount, "f")
    assert payload["rate_value"] == format(expected_rate, "f")
    assert all(
        isinstance(payload[field], str)
        for field in ("source_amount", "converted_amount", "rate_value")
    )
    assert payload["source_currency"] == "EUR"
    assert payload["target_currency"] == "BTC"
    assert payload["rate_context"]["snapshot_id"] == str(SNAPSHOT_ID)
    assert payload["rate_context"]["source_rate"] == {
        "currency": "EUR",
        "provider_name": "BNM",
        "effective_at": "2026-10-27T09:00:00Z",
        "freshness_state": "fallback",
        "is_fallback": True,
        "is_stale": False,
    }
    assert payload["rate_context"]["target_rate"] == {
        "currency": "BTC",
        "provider_name": "CoinGecko",
        "effective_at": "2026-10-28T11:45:00Z",
        "freshness_state": "cached",
        "is_fallback": False,
        "is_stale": True,
    }
    assert not {
        "provider_name",
        "effective_at",
        "freshness_state",
        "is_fallback",
        "is_stale",
    }.intersection(payload)


def test_same_currency_contract_preserves_amount_and_applicable_provenance() -> None:
    with _client(_snapshot()) as client:
        response = _post(client, "123.4500", "EUR", "EUR")

    assert response.status_code == 200
    payload = response.json()
    assert payload["source_amount"] == "123.4500"
    assert payload["converted_amount"] == "123.4500"
    assert payload["rate_value"] == "1"
    assert payload["rate_context"]["source_rate"] == payload["rate_context"][
        "target_rate"
    ]
    assert payload["rate_context"]["source_rate"]["currency"] == "EUR"


@pytest.mark.parametrize(
    ("source", "target"),
    [("EUR", "BTC"), ("BTC", "EUR")],
)
def test_reverse_pair_contract_uses_requested_rate_order(
    source: str,
    target: str,
) -> None:
    snapshot = _snapshot()
    source_entry = snapshot.get_rate(source)
    target_entry = snapshot.get_rate(target)
    assert source_entry is not None
    assert target_entry is not None
    expected_rate = (
        source_entry.normalized_rate_to_mdl / target_entry.normalized_rate_to_mdl
    )
    expected_amount = Decimal(AMOUNT) * expected_rate

    with _client(snapshot) as client:
        response = _post(client, AMOUNT, source, target)

    assert response.status_code == 200
    payload = response.json()
    assert payload["source_currency"] == source
    assert payload["target_currency"] == target
    assert payload["rate_value"] == format(expected_rate, "f")
    assert payload["converted_amount"] == format(expected_amount, "f")
    assert payload["rate_context"]["source_rate"]["currency"] == source
    assert payload["rate_context"]["target_rate"]["currency"] == target


@pytest.mark.parametrize(
    ("amount", "source", "target"),
    [
        ("", "EUR", "BTC"),
        ("0", "EUR", "BTC"),
        ("-1", "EUR", "BTC"),
        ("not-a-number", "EUR", "BTC"),
        ("NaN", "EUR", "BTC"),
        ("Infinity", "EUR", "BTC"),
        (AMOUNT, "ZZZ", "BTC"),
        (AMOUNT, "EUR", "ZZZ"),
        (AMOUNT, "", "BTC"),
        (AMOUNT, "EUR", ""),
    ],
)
def test_business_invalid_inputs_return_sanitized_422(
    amount: str,
    source: str,
    target: str,
) -> None:
    with _client(_snapshot()) as client:
        response = _post(client, amount, source, target)

    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "invalid_conversion_input",
            "message": "Amount and currencies must be valid and supported.",
        }
    }
    assert "Traceback" not in response.text
    assert "database" not in response.text.lower()
    assert "coingecko" not in response.text.lower()
    assert "bnm" not in response.text.lower()


def test_structural_request_validation_remains_pydantic_owned() -> None:
    with _client(_snapshot()) as client:
        response = client.post(
            "/api/v1/convert",
            json={
                "amount": 1.25,
                "source_currency": "EUR",
                "target_currency": "BTC",
            },
        )

    assert response.status_code == 422
    assert response.json()["detail"]
    assert "error" not in response.json()


@pytest.mark.parametrize(
    ("source", "target", "missing_currency"),
    [
        ("ETH", "EUR", "ETH"),
        ("EUR", "ETH", "ETH"),
    ],
)
def test_missing_rate_returns_identified_rate_unavailable_error(
    source: str,
    target: str,
    missing_currency: str,
) -> None:
    snapshot = _snapshot(
        (
            _rate(
                "EUR",
                "20.176000000000000001",
                "BNM",
                CurrencyType.FIAT,
                FIAT_EFFECTIVE_AT,
            ),
            _rate(
                "BTC",
                "1465834.123456789012345678",
                "CoinGecko",
                CurrencyType.CRYPTO,
                CRYPTO_EFFECTIVE_AT,
            ),
        )
    )
    with _client(snapshot) as client:
        response = _post(client, AMOUNT, source, target)

    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "rate_unavailable",
            "message": f"No usable rate is available for {missing_currency}.",
        }
    }


def test_unavailable_snapshot_returns_sanitized_503() -> None:
    with _client(None) as client:
        response = _post(client)

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "conversion_unavailable",
            "message": "Conversion is currently unavailable.",
        }
    }


def test_application_conversion_errors_use_sanitized_contract() -> None:
    with _client(
        use_case_error=InvalidConversionInputError("internal detail"),
    ) as client:
        response = _post(client)

    assert response.status_code == 422
    assert "internal detail" not in response.text
    assert "Traceback" not in response.text


def test_conversion_openapi_documents_request_response_and_freshness_contract() -> None:
    openapi = create_app().openapi()
    operation = openapi["paths"]["/api/v1/convert"]["post"]
    schemas = openapi["components"]["schemas"]
    request_ref = operation["requestBody"]["content"]["application/json"]["schema"][
        "$ref"
    ]
    response_ref = operation["responses"]["200"]["content"]["application/json"][
        "schema"
    ]["$ref"]
    request_schema = schemas[request_ref.rsplit("/", 1)[-1]]
    response_schema = schemas[response_ref.rsplit("/", 1)[-1]]

    assert request_ref.endswith("/ConversionRequest")
    assert response_ref.endswith("/ConversionResponse")
    assert request_schema["properties"]["amount"]["type"] == "string"
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
    assert leg_schema["properties"]["is_fallback"]["type"] == "boolean"
    assert leg_schema["properties"]["is_stale"]["type"] == "boolean"
    assert leg_schema["properties"]["freshness_state"]["$ref"].endswith(
        "/FreshnessState"
    )
    assert set(schemas["FreshnessState"]["enum"]) == {
        "live",
        "fallback",
        "cached",
    }
