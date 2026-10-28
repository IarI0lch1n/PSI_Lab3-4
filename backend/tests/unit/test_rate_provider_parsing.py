"""Provider-independent contract tests for current rate payload parsing."""

from collections.abc import Mapping
from datetime import UTC, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import httpx
import pytest

from app.core.config.settings import Settings
from app.domain.entities.currency import (
    SUPPORTED_CRYPTO_CURRENCIES,
    SUPPORTED_FIAT_CURRENCIES,
)
from app.domain.enums.currency_type import CurrencyType
from app.infrastructure.providers.bnm_rate_provider import (
    BnmRateProvider,
    BnmRateProviderError,
)
from app.infrastructure.providers.coingecko_rate_provider import (
    CoinGeckoRateProvider,
    CoinGeckoRateProviderError,
)


_BNM_DATE = "27.10.2026"
_BNM_EFFECTIVE_AT = datetime(
    2026,
    10,
    27,
    tzinfo=ZoneInfo("Europe/Chisinau"),
)
_COINGECKO_TIMESTAMP = 1_798_560_000
_COINGECKO_IDS: Mapping[str, str] = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "BNB": "binancecoin",
    "XRP": "ripple",
    "ADA": "cardano",
    "DOGE": "dogecoin",
    "USDT": "tether",
}


def _bnm_row(code: str, nominal: str, value: str) -> str:
    return (
        "<Valute>"
        f"<CharCode>{code}</CharCode>"
        f"<Nominal>{nominal}</Nominal>"
        f"<Value>{value}</Value>"
        "</Valute>"
    )


def _bnm_xml(
    *,
    omit: str | None = None,
    extra_rows: tuple[str, ...] = (),
) -> str:
    rows = [
        _bnm_row(code, "1", "17.5")
        for code in SUPPORTED_FIAT_CURRENCIES
        if code not in {"MDL", omit}
    ]
    rows.extend(extra_rows)
    rows = [
        (
            _bnm_row("RON", "100", "391.2345678901234567")
            if "<CharCode>RON</CharCode>" in row
            else row
        )
        for row in rows
    ]
    return f'<ValCurs Date="{_BNM_DATE}">{"".join(rows)}</ValCurs>'


def _coin_json(
    *,
    omit: str | None = None,
    overrides: Mapping[str, tuple[str, str]] | None = None,
) -> str:
    entries = []
    for index, (currency, coin_id) in enumerate(_COINGECKO_IDS.items(), start=1):
        if currency == omit:
            continue
        price, timestamp = (
            overrides[currency]
            if overrides is not None and currency in overrides
            else (
                f"{index}.400000000000000001",
                str(_COINGECKO_TIMESTAMP + index),
            )
        )
        entries.append(
            f'"{coin_id}":{{"mdl":{price},"last_updated_at":{timestamp}}}'
        )
    return "{" + ",".join(entries) + "}"


def _coin_provider_payload(payload: str) -> tuple[CoinGeckoRateProvider, httpx.AsyncClient]:
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, text=payload, request=request)
        )
    )
    provider = CoinGeckoRateProvider(
        client=client,
        settings=Settings(
            coingecko_base_url="https://coingecko.test/api/v3",
            coingecko_max_retries=0,
        ),
    )
    return provider, client


def test_bnm_xml_parses_canonical_fiat_entries_as_exact_decimals() -> None:
    rates = BnmRateProvider._parse_xml(
        _bnm_xml(extra_rows=(_bnm_row("XYZ", "1", "9.99"),))
    )
    expected_codes = tuple(
        code for code in SUPPORTED_FIAT_CURRENCIES if code != "MDL"
    )

    assert tuple(rate.currency for rate in rates) == expected_codes
    assert len(rates) == 9
    for rate in rates:
        assert rate.provider_name == "BNM"
        assert rate.provider_type is CurrencyType.FIAT
        assert rate.effective_at == _BNM_EFFECTIVE_AT
        assert isinstance(rate.normalized_rate_to_mdl, Decimal)
        assert not isinstance(rate.normalized_rate_to_mdl, float)
    assert "XYZ" not in {rate.currency for rate in rates}
    assert "MDL" not in {rate.currency for rate in rates}


def test_bnm_nominal_normalization_preserves_decimal_precision_and_unit() -> None:
    (rate,) = BnmRateProvider._parse_xml(
        f'<ValCurs Date="{_BNM_DATE}">'
        f'{_bnm_row("RON", "100", "391.2345678901234567")}'
        "</ValCurs>"
    )

    assert rate.normalized_rate_to_mdl == Decimal("3.912345678901234567")
    assert rate.nominal_unit == 100


def test_bnm_decimal_comma_is_parsed_exactly() -> None:
    (rate,) = BnmRateProvider._parse_xml(
        f'<ValCurs Date="{_BNM_DATE}">'
        f'{_bnm_row("USD", "10", "175,50")}'
        "</ValCurs>"
    )

    assert rate.normalized_rate_to_mdl == Decimal("17.55")
    assert rate.nominal_unit == 10


@pytest.mark.asyncio
async def test_bnm_empty_response_raises_provider_error() -> None:
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, text="   ", request=request)
        )
    )
    provider = BnmRateProvider(
        client=client,
        settings=Settings(
            bnm_base_url="https://bnm.test/official_exchange_rates",
            bnm_max_retries=0,
        ),
        today_provider=lambda: datetime(2026, 10, 27).date(),
    )
    try:
        with pytest.raises(BnmRateProviderError, match="empty XML"):
            await provider.fetch_latest_rates()
    finally:
        await client.aclose()


def test_bnm_malformed_xml_raises_provider_error() -> None:
    with pytest.raises(BnmRateProviderError, match="malformed XML"):
        BnmRateProvider._parse_xml("<ValCurs><Valute>")


@pytest.mark.parametrize(
    ("nominal", "value"),
    [
        ("0", "17.5"),
        ("-1", "17.5"),
        ("1", "0"),
        ("1", "-0.01"),
        ("1", "not-a-number"),
    ],
)
def test_bnm_rejects_invalid_nominal_or_rate(nominal: str, value: str) -> None:
    with pytest.raises(BnmRateProviderError):
        BnmRateProvider._parse_xml(
            f'<ValCurs Date="{_BNM_DATE}">'
            f'{_bnm_row("USD", nominal, value)}'
            "</ValCurs>"
        )


def test_coingecko_json_maps_all_supported_ids_and_preserves_decimal_values() -> None:
    rates = CoinGeckoRateProvider._parse_response(_coin_json())

    assert tuple(rate.currency for rate in rates) == tuple(
        SUPPORTED_CRYPTO_CURRENCIES
    )
    assert len(rates) == 8
    for index, rate in enumerate(rates, start=1):
        assert rate.currency == tuple(SUPPORTED_CRYPTO_CURRENCIES)[index - 1]
        assert rate.normalized_rate_to_mdl == Decimal(
            f"{index}.400000000000000001"
        )
        assert rate.nominal_unit == 1
        assert rate.provider_name == "CoinGecko"
        assert rate.provider_type is CurrencyType.CRYPTO
        assert rate.effective_at == datetime.fromtimestamp(
            _COINGECKO_TIMESTAMP + index,
            tz=UTC,
        )
        assert isinstance(rate.normalized_rate_to_mdl, Decimal)
        assert not isinstance(rate.normalized_rate_to_mdl, float)


@pytest.mark.parametrize("payload", ["{}", "{", "[]"])
def test_coingecko_empty_or_malformed_json_is_rejected(payload: str) -> None:
    with pytest.raises(CoinGeckoRateProviderError):
        CoinGeckoRateProvider._parse_response(payload)


def test_coingecko_missing_required_currency_rejects_partial_result() -> None:
    with pytest.raises(CoinGeckoRateProviderError, match="missing requested coin"):
        CoinGeckoRateProvider._parse_response(_coin_json(omit="USDT"))


@pytest.mark.parametrize(
    "price",
    ["0", "-1", '"not-a-number"', "true"],
)
def test_coingecko_rejects_non_positive_or_non_numeric_prices(price: str) -> None:
    payload = _coin_json(overrides={"BTC": (price, str(_COINGECKO_TIMESTAMP))})
    with pytest.raises(CoinGeckoRateProviderError):
        CoinGeckoRateProvider._parse_response(payload)


@pytest.mark.parametrize(
    "timestamp",
    ["null", '"not-a-timestamp"', "0", "-1", "1.5"],
)
def test_coingecko_rejects_invalid_effective_timestamps(timestamp: str) -> None:
    payload = _coin_json(
        overrides={"BTC": ("17.4", timestamp)}
    )
    with pytest.raises(CoinGeckoRateProviderError, match="last_updated_at"):
        CoinGeckoRateProvider._parse_response(payload)


@pytest.mark.asyncio
async def test_coingecko_blank_http_response_raises_provider_error() -> None:
    provider, client = _coin_provider_payload(" ")
    try:
        with pytest.raises(CoinGeckoRateProviderError, match="empty JSON"):
            await provider.fetch_latest_rates()
    finally:
        await client.aclose()
