"""Contract tests for shared provider, session, and network-guard fixtures."""

from datetime import datetime, timedelta
from decimal import Decimal

import httpx
import pytest

from app.core.config.settings import Settings
from app.domain.entities.currency import (
    SUPPORTED_CRYPTO_CURRENCIES,
    SUPPORTED_FIAT_CURRENCIES,
)
from app.domain.enums.currency_type import CurrencyType
from app.domain.interfaces.rate_provider import ProviderRate, RateProvider
from app.infrastructure.database.unit_of_work import SqlAlchemyUnitOfWork
from app.infrastructure.providers.bnm_rate_provider import BnmRateProvider
from app.infrastructure.providers.coingecko_rate_provider import (
    CoinGeckoRateProvider,
)
from tests.fixtures.fake_rate_providers import (
    FakeBnmRateProvider,
    FakeCoinGeckoRateProvider,
    FakeRateProvider,
    HistoricalRateRequest,
    IsolatedSession,
    make_provider_rate,
)


def test_fake_providers_implement_rate_provider_and_return_configured_latest(
    fixed_utc_now: datetime,
    complete_fiat_provider_rates: tuple[ProviderRate, ...],
    complete_crypto_provider_rates: tuple[ProviderRate, ...],
) -> None:
    fiat = FakeBnmRateProvider(latest_rates=complete_fiat_provider_rates)
    crypto = FakeCoinGeckoRateProvider(latest_rates=complete_crypto_provider_rates)

    assert isinstance(fiat, RateProvider)
    assert isinstance(crypto, RateProvider)
    assert len(complete_fiat_provider_rates) == 9
    assert len(complete_crypto_provider_rates) == 8
    assert all(rate.effective_at == fixed_utc_now for rate in complete_fiat_provider_rates)
    assert all(rate.effective_at == fixed_utc_now for rate in complete_crypto_provider_rates)


@pytest.mark.asyncio
async def test_fake_latest_calls_return_values_or_raise_configured_error(
    complete_fiat_provider_rates: tuple[ProviderRate, ...],
) -> None:
    provider = FakeBnmRateProvider(latest_rates=complete_fiat_provider_rates)

    assert await provider.fetch_latest_rates() == complete_fiat_provider_rates
    assert provider.latest_call_count == 1

    expected_error = RuntimeError("controlled provider outage")
    failing_provider = FakeBnmRateProvider(latest_error=expected_error)
    with pytest.raises(RuntimeError, match="controlled provider outage"):
        await failing_provider.fetch_latest_rates()
    assert failing_provider.latest_call_count == 1


@pytest.mark.asyncio
async def test_fake_historical_calls_return_configured_data_and_record_arguments(
    fixed_utc_now: datetime,
) -> None:
    historical_rate = make_provider_rate("USD", Decimal("17.25"))
    provider = FakeBnmRateProvider(historical_rates=[historical_rate])
    start_at = fixed_utc_now - timedelta(days=7)
    currency_codes = ["USD", "EUR"]

    rates = await provider.fetch_historical_rates(
        currency_codes,
        start_at,
        fixed_utc_now,
    )

    assert rates == (historical_rate,)
    assert provider.historical_call_count == 1
    assert provider.historical_requests == [
        HistoricalRateRequest(tuple(currency_codes), start_at, fixed_utc_now)
    ]

    expected_error = RuntimeError("controlled history failure")
    failing_provider = FakeCoinGeckoRateProvider(
        historical_error=expected_error
    )
    with pytest.raises(RuntimeError, match="controlled history failure"):
        await failing_provider.fetch_historical_rates(
            currency_codes,
            start_at,
            fixed_utc_now,
        )
    assert failing_provider.historical_call_count == 1


@pytest.mark.asyncio
async def test_fake_provider_metadata_is_stable() -> None:
    assert await FakeBnmRateProvider().get_metadata() == {
        "provider_name": "Fake BNM",
        "provider_type": "fiat",
    }
    assert await FakeCoinGeckoRateProvider().get_metadata() == {
        "provider_name": "Fake CoinGecko",
        "provider_type": "crypto",
    }


def test_complete_fixtures_use_canonical_codes_decimal_rates_and_aware_times(
    complete_fiat_provider_rates: tuple[ProviderRate, ...],
    complete_crypto_provider_rates: tuple[ProviderRate, ...],
    fixed_utc_now: datetime,
) -> None:
    fiat_codes = {rate.currency for rate in complete_fiat_provider_rates}
    crypto_codes = {rate.currency for rate in complete_crypto_provider_rates}

    assert fiat_codes == set(SUPPORTED_FIAT_CURRENCIES) - {"MDL"}
    assert "MDL" not in fiat_codes
    assert crypto_codes == set(SUPPORTED_CRYPTO_CURRENCIES)
    assert all(
        isinstance(rate.normalized_rate_to_mdl, Decimal)
        and rate.normalized_rate_to_mdl > 0
        for rate in (*complete_fiat_provider_rates, *complete_crypto_provider_rates)
    )
    assert all(
        rate.effective_at.tzinfo is not None
        and rate.effective_at.utcoffset() is not None
        and rate.effective_at == fixed_utc_now
        for rate in (*complete_fiat_provider_rates, *complete_crypto_provider_rates)
    )
    assert all(rate.provider_type is CurrencyType.FIAT for rate in complete_fiat_provider_rates)
    assert all(rate.provider_type is CurrencyType.CRYPTO for rate in complete_crypto_provider_rates)


@pytest.mark.asyncio
async def test_fake_providers_never_use_http_clients(monkeypatch) -> None:
    def fail_if_http_used(*args, **kwargs):
        del args, kwargs
        raise AssertionError("Fake providers must not make HTTP requests.")

    monkeypatch.setattr(httpx.AsyncClient, "send", fail_if_http_used)
    provider = FakeBnmRateProvider()

    await provider.fetch_latest_rates()
    assert provider.latest_call_count == 1


def test_isolated_session_factory_injects_into_uow_without_engine(
    isolated_sqlalchemy_session: IsolatedSession,
    isolated_session_factory,
) -> None:
    uow = SqlAlchemyUnitOfWork(session_factory=isolated_session_factory)

    assert uow.currency_repository is not None
    assert uow.rate_repository is not None
    with uow:
        pass
    assert isolated_sqlalchemy_session.rollback_calls == 1
    assert isolated_sqlalchemy_session.close_calls == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url",
    [
        "https://www.bnm.md/en/official_exchange_rates",
        "https://api.coingecko.com/api/v3/simple/price",
        "https://pro-api.coingecko.com/api/v3/simple/price",
    ],
)
async def test_live_provider_hosts_are_rejected_before_mock_transport(url: str) -> None:
    transport_calls: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        transport_calls.append(request)
        return httpx.Response(200, request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(AssertionError, match="must not contact live providers"):
            await client.get(url)

    assert transport_calls == []


@pytest.mark.asyncio
async def test_mocktransport_test_host_remains_allowed() -> None:
    transport_calls: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        transport_calls.append(request)
        return httpx.Response(200, text="ok", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        response = await client.get("https://bnm.test/rates")

    assert response.status_code == 200
    assert response.text == "ok"
    assert len(transport_calls) == 1


@pytest.mark.asyncio
async def test_default_provider_urls_are_guarded_before_any_network_call() -> None:
    settings = Settings(
        bnm_base_url="https://www.bnm.md/en/official_exchange_rates",
        bnm_max_retries=0,
        coingecko_base_url="https://api.coingecko.com/api/v3",
        coingecko_max_retries=0,
    )

    with pytest.raises(AssertionError, match="must not contact live providers"):
        await BnmRateProvider(settings=settings).fetch_latest_rates()
    with pytest.raises(AssertionError, match="must not contact live providers"):
        await CoinGeckoRateProvider(settings=settings).fetch_latest_rates()
