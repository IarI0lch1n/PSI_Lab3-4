"""Tests for BNM current-rate fetching and XML normalization."""

from collections.abc import Callable
from datetime import UTC, date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import httpx
import pytest

from app.core.config.settings import Settings
from app.domain.entities.currency import SUPPORTED_FIAT_CURRENCIES
from app.domain.enums.currency_type import CurrencyType
from app.infrastructure.providers.bnm_rate_provider import (
    BnmRateProvider,
    BnmRateProviderError,
)


_BASE_URL = "https://bnm.test/official_exchange_rates"
_REQUEST_DATE = date(2026, 10, 28)


def _xml_row(code: str | None, nominal: str | None, value: str | None) -> str:
    fields = []
    if code is not None:
        fields.append(f"<CharCode>{code}</CharCode>")
    if nominal is not None:
        fields.append(f"<Nominal>{nominal}</Nominal>")
    if value is not None:
        fields.append(f"<Value>{value}</Value>")
    return f"<Valute>{''.join(fields)}</Valute>"


def _xml(*rows: str, root_date: str = "28.10.2026") -> str:
    return f'<ValCurs Date="{root_date}">{"".join(rows)}</ValCurs>'


def _provider(
    handler: Callable[[httpx.Request], httpx.Response],
    *,
    retries: int = 0,
) -> tuple[BnmRateProvider, httpx.AsyncClient]:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    settings = Settings(
        bnm_base_url=_BASE_URL,
        bnm_timeout_seconds=1,
        bnm_max_retries=retries,
    )
    provider = BnmRateProvider(
        client=client,
        settings=settings,
        today_provider=lambda: _REQUEST_DATE,
    )
    return provider, client


async def _fetch_xml(xml: str) -> tuple:
    provider, client = _provider(
        lambda request: httpx.Response(200, text=xml, request=request)
    )
    try:
        return await provider.fetch_latest_rates()
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_fetch_requests_current_moldova_date_and_maps_provider_metadata() -> None:
    xml = _xml(
        _xml_row("USD", "1", "17.123456789012345678901"),
        _xml_row("JPY", "100", "11.4754"),
    )
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, text=xml, request=request)

    provider, client = _provider(handler)
    try:
        rates = await provider.fetch_latest_rates()
        metadata = await provider.get_metadata()
    finally:
        await client.aclose()

    assert len(requests) == 1
    assert str(requests[0].url) == (
        f"{_BASE_URL}?get_xml=1&date=28.10.2026"
    )
    assert [rate.currency for rate in rates] == ["USD", "JPY"]
    assert rates[0].normalized_rate_to_mdl == Decimal(
        "17.123456789012345678901"
    )
    assert rates[0].nominal_unit == 1
    assert rates[1].normalized_rate_to_mdl == Decimal("0.114754")
    assert rates[1].nominal_unit == 100
    assert rates[0].provider_name == rates[1].provider_name == "BNM"
    assert rates[0].provider_type is CurrencyType.FIAT
    assert rates[0].effective_at == datetime(
        2026, 10, 28, 0, 0, tzinfo=ZoneInfo("Europe/Chisinau")
    )
    assert rates[0].effective_at.tzinfo is not None
    assert rates[0].effective_at.utcoffset() is not None
    assert metadata == {
        "provider_name": "BNM",
        "provider_type": "fiat",
        "base_url": _BASE_URL,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("nominal", "value", "expected"),
    [
        ("1", "17.5", Decimal("17.5")),
        ("10", "175.0", Decimal("17.50")),
        ("100", "11.4754", Decimal("0.114754")),
    ],
)
async def test_nominal_normalization(
    nominal: str,
    value: str,
    expected: Decimal,
) -> None:
    (rate,) = await _fetch_xml(_xml(_xml_row("USD", nominal, value)))

    assert rate.normalized_rate_to_mdl == expected
    assert rate.nominal_unit == int(nominal)


@pytest.mark.asyncio
async def test_filters_unsupported_currencies_and_does_not_synthesize_mdl() -> None:
    rates = await _fetch_xml(
        _xml(
            _xml_row("USD", "1", "17.5"),
            _xml_row("ABC", "1", "5"),
        )
    )

    assert [rate.currency for rate in rates] == ["USD"]
    assert "MDL" in SUPPORTED_FIAT_CURRENCIES


@pytest.mark.asyncio
async def test_trims_fields_and_accepts_decimal_comma() -> None:
    rates = await _fetch_xml(
        _xml(_xml_row(" USD ", " 10 ", " 175,50 "))
    )

    assert rates[0].currency == "USD"
    assert rates[0].nominal_unit == 10
    assert rates[0].normalized_rate_to_mdl == Decimal("17.55")


@pytest.mark.asyncio
@pytest.mark.parametrize("body", ["", "   "])
async def test_empty_xml_body_raises_provider_error(body: str) -> None:
    provider, client = _provider(
        lambda request: httpx.Response(200, text=body, request=request)
    )
    try:
        with pytest.raises(BnmRateProviderError, match="empty XML"):
            await provider.fetch_latest_rates()
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_malformed_xml_raises_provider_error() -> None:
    with pytest.raises(BnmRateProviderError, match="malformed XML"):
        await _fetch_xml("<ValCurs><Valute>")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("row", "message"),
    [
        (_xml_row(None, "1", "17.5"), "without CharCode"),
        (_xml_row("USD", None, "17.5"), "invalid Nominal"),
        (_xml_row("USD", "0", "17.5"), "Nominal must be positive"),
        (_xml_row("USD", "-2", "17.5"), "Nominal must be positive"),
        (_xml_row("USD", "not-an-integer", "17.5"), "invalid Nominal"),
        (_xml_row("USD", "1", None), "missing Value"),
        (_xml_row("USD", "1", "not-a-number"), "non-numeric Value"),
        (_xml_row("USD", "1", "NaN"), "non-positive or invalid"),
        (_xml_row("USD", "1", "Infinity"), "non-positive or invalid"),
        (_xml_row("USD", "1", "0"), "non-positive"),
        (_xml_row("USD", "1", "-1"), "non-positive"),
    ],
)
async def test_invalid_supported_rows_raise_provider_error(
    row: str,
    message: str,
) -> None:
    with pytest.raises(BnmRateProviderError, match=message):
        await _fetch_xml(_xml(row))


@pytest.mark.asyncio
@pytest.mark.parametrize("root_date", ["", "2026-10-28", "32.10.2026"])
async def test_missing_or_invalid_root_date_raises_provider_error(
    root_date: str,
) -> None:
    with pytest.raises(BnmRateProviderError, match="root Date"):
        await _fetch_xml(
            _xml(_xml_row("USD", "1", "17.5"), root_date=root_date)
        )


@pytest.mark.asyncio
async def test_duplicate_supported_currency_raises_provider_error() -> None:
    with pytest.raises(BnmRateProviderError, match="duplicate supported currency"):
        await _fetch_xml(
            _xml(
                _xml_row("USD", "1", "17.5"),
                _xml_row(" usd ", "1", "17.6"),
            )
        )


@pytest.mark.asyncio
async def test_no_supported_currency_rows_raises_provider_error() -> None:
    with pytest.raises(BnmRateProviderError, match="no supported usable"):
        await _fetch_xml(_xml(_xml_row("ABC", "1", "5")))


@pytest.mark.asyncio
async def test_http_failure_raises_provider_error_without_live_network() -> None:
    provider, client = _provider(
        lambda request: httpx.Response(503, request=request)
    )
    try:
        with pytest.raises(BnmRateProviderError, match="HTTP status 503"):
            await provider.fetch_latest_rates()
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_transient_http_error_retries_using_configured_limit() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        status = 503 if calls == 1 else 200
        body = _xml(_xml_row("USD", "1", "17.5")) if status == 200 else ""
        return httpx.Response(status, text=body, request=request)

    provider, client = _provider(handler, retries=1)
    try:
        rates = await provider.fetch_latest_rates()
    finally:
        await client.aclose()

    assert calls == 2
    assert rates[0].normalized_rate_to_mdl == Decimal("17.5")


@pytest.mark.asyncio
async def test_historical_fetching_is_explicitly_deferred_to_t042() -> None:
    provider = BnmRateProvider(
        settings=Settings(bnm_base_url=_BASE_URL),
        today_provider=lambda: _REQUEST_DATE,
    )

    with pytest.raises(NotImplementedError, match="T042"):
        await provider.fetch_historical_rates(
            ["USD"],
            datetime(2026, 10, 1, tzinfo=UTC),
            datetime(2026, 10, 28, tzinfo=UTC),
        )
