"""Tests for CoinGecko current-rate fetching and normalization."""

import json
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal

import httpx
import pytest

from app.core.config.settings import Settings
from app.domain.entities.currency import SUPPORTED_CRYPTO_CURRENCIES
from app.domain.enums.currency_type import CurrencyType
from app.infrastructure.providers.coingecko_rate_provider import (
    CoinGeckoRateProvider,
    CoinGeckoRateProviderError,
)


_BASE_URL = "https://coingecko.test/api/v3"
_COIN_IDS = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "BNB": "binancecoin",
    "XRP": "ripple",
    "ADA": "cardano",
    "DOGE": "dogecoin",
    "USDT": "tether",
}
_TIMESTAMP = 1_798_560_000


def _payload(
    *,
    omit: str | None = None,
    mutate: Callable[[dict[str, object]], None] | None = None,
) -> dict[str, object]:
    data: dict[str, object] = {
        coin_id: {
            "mdl": Decimal(f"{index}.123456789012345678901"),
            "last_updated_at": _TIMESTAMP + index,
        }
        for index, coin_id in enumerate(_COIN_IDS.values(), start=1)
        if coin_id != omit
    }
    if mutate is not None:
        mutate(data)
    return data


def _encoded(payload: object) -> str:
    body = json.dumps(payload, default=str)
    if isinstance(payload, dict):
        prices = payload.get("prices")
        if isinstance(prices, list):
            for point in prices:
                if not isinstance(point, list):
                    continue
                for value in point:
                    if isinstance(value, Decimal):
                        body = body.replace(
                            json.dumps(str(value)),
                            str(value),
                            1,
                        )
        for coin_data in payload.values():
            if not isinstance(coin_data, dict):
                continue
            price = coin_data.get("mdl")
            if isinstance(price, Decimal):
                quoted = json.dumps(str(price))
                body = body.replace(f'"mdl": {quoted}', f'"mdl": {price}', 1)
    return body


def _provider(
    handler: Callable[[httpx.Request], httpx.Response],
    *,
    api_key: str = "placeholder_coingecko_api_key",
    retries: int = 0,
) -> tuple[CoinGeckoRateProvider, httpx.AsyncClient]:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    settings = Settings(
        coingecko_base_url=_BASE_URL,
        coingecko_api_key=api_key,
        coingecko_timeout_seconds=1,
        coingecko_max_retries=retries,
    )
    return CoinGeckoRateProvider(client=client, settings=settings), client


async def _fetch(
    payload: object,
) -> tuple:
    provider, client = _provider(
        lambda request: httpx.Response(
            200,
            text=_encoded(payload),
            request=request,
        )
    )
    try:
        return await provider.fetch_latest_rates()
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_requests_all_coin_ids_in_one_mdl_price_request() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, text=_encoded(_payload()), request=request)

    provider, client = _provider(handler)
    try:
        rates = await provider.fetch_latest_rates()
    finally:
        await client.aclose()

    assert len(requests) == 1
    request = requests[0]
    assert request.url.path == "/api/v3/simple/price"
    assert request.url.params["ids"] == ",".join(_COIN_IDS.values())
    assert request.url.params["vs_currencies"] == "mdl"
    assert request.url.params["include_last_updated_at"] == "true"
    assert tuple(rate.currency for rate in rates) == tuple(
        SUPPORTED_CRYPTO_CURRENCIES
    )
    assert len(rates) == 8


@pytest.mark.asyncio
async def test_maps_ids_to_currency_codes_and_provider_metadata() -> None:
    rates = await _fetch(_payload())

    for rate, currency_code in zip(
        rates,
        SUPPORTED_CRYPTO_CURRENCIES,
        strict=True,
    ):
        index = tuple(SUPPORTED_CRYPTO_CURRENCIES).index(currency_code) + 1
        assert rate.currency == currency_code
        assert rate.normalized_rate_to_mdl == Decimal(
            f"{index}.123456789012345678901"
        )
        assert rate.nominal_unit == 1
        assert rate.provider_name == "CoinGecko"
        assert rate.provider_type is CurrencyType.CRYPTO
        assert rate.effective_at == datetime.fromtimestamp(
            _TIMESTAMP + index,
            tz=UTC,
        )
        assert rate.effective_at.tzinfo is UTC


@pytest.mark.asyncio
async def test_api_key_uses_header_and_is_not_exposed_in_metadata_or_url() -> None:
    api_key = "private-test-key"
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, text=_encoded(_payload()), request=request)

    provider, client = _provider(handler, api_key=api_key)
    try:
        await provider.fetch_latest_rates()
        metadata = await provider.get_metadata()
    finally:
        await client.aclose()

    assert captured[0].headers["x-cg-demo-api-key"] == api_key
    assert api_key not in str(captured[0].url)
    assert api_key not in repr(metadata)
    assert metadata == {
        "provider_name": "CoinGecko",
        "provider_type": "crypto",
        "base_url": _BASE_URL,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "api_key",
    [
        "placeholder_coingecko_api_key",
        " ",
        "YOUR_API_KEY",
        "replace_me_now",
        "changeme",
    ],
)
async def test_placeholder_or_blank_api_key_is_not_sent(api_key: str) -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, text=_encoded(_payload()), request=request)

    provider, client = _provider(handler, api_key=api_key)
    try:
        await provider.fetch_latest_rates()
    finally:
        await client.aclose()

    assert "x-cg-demo-api-key" not in captured[0].headers


@pytest.mark.asyncio
async def test_empty_body_and_malformed_json_raise_provider_error() -> None:
    for body, message in [("", "empty JSON"), ("{", "malformed JSON")]:
        provider, client = _provider(
            lambda request, response_body=body: httpx.Response(
                200,
                text=response_body,
                request=request,
            )
        )
        try:
            with pytest.raises(CoinGeckoRateProviderError, match=message):
                await provider.fetch_latest_rates()
        finally:
            await client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize("body", ['[]', '"not an object"', "null"])
async def test_non_object_top_level_raises_provider_error(body: str) -> None:
    provider, client = _provider(
        lambda request: httpx.Response(200, text=body, request=request)
    )
    try:
        with pytest.raises(CoinGeckoRateProviderError, match="must be an object"):
            await provider.fetch_latest_rates()
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_missing_required_coin_rejects_partial_result() -> None:
    with pytest.raises(CoinGeckoRateProviderError, match="missing requested coin"):
        await _fetch(_payload(omit="tether"))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("coin_value", "message"),
    [
        ([], "must be an object"),
        ({}, "missing mdl"),
        ({"mdl": None, "last_updated_at": _TIMESTAMP}, "invalid mdl"),
        ({"mdl": "12.5", "last_updated_at": _TIMESTAMP}, "invalid mdl"),
        ({"mdl": True, "last_updated_at": _TIMESTAMP}, "invalid mdl"),
        ({"mdl": 0, "last_updated_at": _TIMESTAMP}, "non-positive"),
        ({"mdl": -1, "last_updated_at": _TIMESTAMP}, "non-positive"),
        ({"mdl": Decimal("NaN"), "last_updated_at": _TIMESTAMP}, "non-finite"),
        (
            {"mdl": Decimal("Infinity"), "last_updated_at": _TIMESTAMP},
            "non-finite",
        ),
        (
            {"mdl": Decimal("-Infinity"), "last_updated_at": _TIMESTAMP},
            "non-finite",
        ),
    ],
)
async def test_invalid_coin_data_raises_provider_error(
    coin_value: object,
    message: str,
) -> None:
    data = _payload()
    data["bitcoin"] = coin_value

    with pytest.raises(CoinGeckoRateProviderError, match=message):
        await _fetch(data)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "coin_value",
    [
        {"mdl": 1},
        {"mdl": 1, "last_updated_at": None},
        {"mdl": 1, "last_updated_at": True},
        {"mdl": 1, "last_updated_at": "1798560000"},
        {"mdl": 1, "last_updated_at": 0},
        {"mdl": 1, "last_updated_at": -1},
        {"mdl": 1, "last_updated_at": Decimal("1.5")},
        {"mdl": 1, "last_updated_at": Decimal("NaN")},
        {"mdl": 1, "last_updated_at": Decimal("Infinity")},
        {"mdl": 1, "last_updated_at": Decimal("1e100")},
    ],
)
async def test_invalid_last_updated_at_raises_provider_error(
    coin_value: object,
) -> None:
    data = _payload()
    data["bitcoin"] = coin_value

    with pytest.raises(CoinGeckoRateProviderError, match="last_updated_at"):
        await _fetch(data)


@pytest.mark.asyncio
async def test_decimal_json_parsing_preserves_price_precision_without_float() -> None:
    rates = await _fetch(_payload())
    rate = rates[0]

    assert rate.normalized_rate_to_mdl == Decimal(
        "1.123456789012345678901"
    )
    assert not isinstance(rate.normalized_rate_to_mdl, float)


@pytest.mark.asyncio
async def test_http_permanent_failure_does_not_retry_or_leak_key() -> None:
    calls = 0
    api_key = "private-test-key"

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(400, request=request)

    provider, client = _provider(handler, api_key=api_key, retries=2)
    try:
        with pytest.raises(CoinGeckoRateProviderError) as error:
            await provider.fetch_latest_rates()
    finally:
        await client.aclose()

    assert calls == 1
    assert api_key not in str(error.value)


@pytest.mark.asyncio
async def test_transient_http_failure_retries() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        status = 503 if calls == 1 else 200
        body = _encoded(_payload()) if status == 200 else "temporary error"
        return httpx.Response(status, text=body, request=request)

    provider, client = _provider(handler, retries=1)
    try:
        rates = await provider.fetch_latest_rates()
    finally:
        await client.aclose()

    assert calls == 2
    assert len(rates) == 8


@pytest.mark.asyncio
async def test_transport_failure_retries_without_live_network() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise httpx.ConnectError("network unavailable", request=request)
        return httpx.Response(200, text=_encoded(_payload()), request=request)

    provider, client = _provider(handler, retries=1)
    try:
        rates = await provider.fetch_latest_rates()
    finally:
        await client.aclose()

    assert calls == 2
    assert len(rates) == 8


@pytest.mark.asyncio
async def test_historical_requests_each_selected_coin_and_normalizes_timestamps() -> None:
    start = datetime(2026, 10, 1, tzinfo=UTC)
    middle = datetime(2026, 10, 1, 12, 30, tzinfo=UTC)
    end = datetime(2026, 10, 2, tzinfo=UTC)
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        offset = Decimal("0.000000000000000001")
        body = {
            "prices": [
                [int(start.timestamp() * 1000) - 1, 999],
                [int(start.timestamp() * 1000), Decimal("10.123456789012345678")],
                [int(middle.timestamp() * 1000), Decimal("11.123456789012345678")],
                [int(end.timestamp() * 1000) + 1, 999],
            ]
        }
        if "/ethereum/" in request.url.path:
            for point in body["prices"]:
                point[1] += offset
        return httpx.Response(200, text=_encoded(body), request=request)

    provider, client = _provider(handler, api_key="history-key")
    try:
        rates = await provider.fetch_historical_rates(
            [" eth ", "BTC", "USD"],
            start,
            end,
        )
    finally:
        await client.aclose()

    assert [request.url.path for request in requests] == [
        "/api/v3/coins/bitcoin/market_chart/range",
        "/api/v3/coins/ethereum/market_chart/range",
    ]
    for request in requests:
        assert request.url.params["vs_currency"] == "mdl"
        assert request.url.params["from"] == str(int(start.timestamp()))
        assert request.url.params["to"] == str(int(end.timestamp()))
        assert request.headers["x-cg-demo-api-key"] == "history-key"
    assert [(rate.effective_at, rate.currency) for rate in rates] == [
        (start, "BTC"),
        (start, "ETH"),
        (middle, "BTC"),
        (middle, "ETH"),
    ]
    assert rates[0].normalized_rate_to_mdl == Decimal(
        "10.123456789012345678"
    )
    assert rates[1].normalized_rate_to_mdl == Decimal(
        "10.123456789012345679"
    )
    assert all(rate.provider_name == "CoinGecko" for rate in rates)
    assert all(rate.provider_type is CurrencyType.CRYPTO for rate in rates)
    assert all(rate.nominal_unit == 1 for rate in rates)
    assert all(rate.effective_at.tzinfo is UTC for rate in rates)


@pytest.mark.asyncio
async def test_historical_non_crypto_request_returns_without_http_calls() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(500, request=request)

    provider, client = _provider(handler)
    try:
        rates = await provider.fetch_historical_rates(
            ["USD", "MDL", "UNKNOWN"],
            datetime(2026, 10, 1, tzinfo=UTC),
            datetime(2026, 10, 2, tzinfo=UTC),
        )
    finally:
        await client.aclose()

    assert rates == ()
    assert calls == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("body", "message"),
    [
        ("", "empty historical JSON"),
        ("{", "malformed historical JSON"),
        ('{"prices": {}}', "prices array"),
        ('{"prices": [[1]]}', "invalid point"),
        ('{"prices": [[1, 0]]}', "invalid MDL price"),
        ('{"prices": [[1.5, 1]]}', "invalid timestamp"),
        ('{"prices": [[1000, 1], [1000, 2]]}', "duplicate timestamp"),
    ],
)
async def test_historical_rejects_invalid_payloads(body: str, message: str) -> None:
    provider, client = _provider(
        lambda request: httpx.Response(200, text=body, request=request)
    )
    try:
        with pytest.raises(CoinGeckoRateProviderError, match=message):
            await provider.fetch_historical_rates(
                ["BTC"],
                datetime(1970, 1, 1, tzinfo=UTC),
                datetime(2026, 10, 2, tzinfo=UTC),
            )
    finally:
        await client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("start_at", "end_at", "message"),
    [
        (
            datetime(2026, 10, 1),
            datetime(2026, 10, 2, tzinfo=UTC),
            "start_at must be timezone-aware",
        ),
        (
            datetime(2026, 10, 2, tzinfo=UTC),
            datetime(2026, 10, 1, tzinfo=UTC),
            "must not follow",
        ),
    ],
)
async def test_historical_rejects_invalid_date_windows(
    start_at: datetime,
    end_at: datetime,
    message: str,
) -> None:
    provider, client = _provider(
        lambda request: httpx.Response(500, request=request)
    )
    try:
        with pytest.raises(CoinGeckoRateProviderError, match=message):
            await provider.fetch_historical_rates(["BTC"], start_at, end_at)
    finally:
        await client.aclose()
