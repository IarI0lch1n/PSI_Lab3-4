"""Shared deterministic backend test fixtures and network safety guard."""

from collections.abc import Callable
from datetime import datetime
from decimal import Decimal
from typing import Any

import httpx
import pytest

from app.core.config.settings import Settings
from app.domain.interfaces.rate_provider import ProviderRate
from tests.fixtures.fake_rate_providers import (
    FIXED_UTC_NOW,
    FakeBnmRateProvider,
    FakeCoinGeckoRateProvider,
    FakeRateProvider,
    IsolatedSession,
    QueuedResult,
    make_complete_crypto_rates,
    make_complete_fiat_rates,
)

_BLOCKED_PROVIDER_DOMAINS = ("bnm.md", "coingecko.com")
_LIVE_PROVIDER_MESSAGE = (
    "Automated tests must not contact live providers "
    "(BNM or CoinGecko). Use fake hosts or MockTransport."
)


def _is_live_provider_host(host: str) -> bool:
    normalized_host = host.lower().rstrip(".")
    return any(
        normalized_host == domain or normalized_host.endswith(f".{domain}")
        for domain in _BLOCKED_PROVIDER_DOMAINS
    )


@pytest.fixture(autouse=True)
def prevent_live_provider_http(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject live-provider HTTPX sends before any transport can reach the network."""
    original_async_send = httpx.AsyncClient.send
    original_sync_send = httpx.Client.send

    async def guarded_async_send(
        client: httpx.AsyncClient,
        request: httpx.Request,
        *args: Any,
        **kwargs: Any,
    ) -> httpx.Response:
        if _is_live_provider_host(request.url.host):
            raise AssertionError(_LIVE_PROVIDER_MESSAGE)
        return await original_async_send(client, request, *args, **kwargs)

    def guarded_sync_send(
        client: httpx.Client,
        request: httpx.Request,
        *args: Any,
        **kwargs: Any,
    ) -> httpx.Response:
        if _is_live_provider_host(request.url.host):
            raise AssertionError(_LIVE_PROVIDER_MESSAGE)
        return original_sync_send(client, request, *args, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "send", guarded_async_send)
    monkeypatch.setattr(httpx.Client, "send", guarded_sync_send)


@pytest.fixture
def fixed_utc_now() -> datetime:
    return FIXED_UTC_NOW


@pytest.fixture
def complete_fiat_provider_rates(
    fixed_utc_now: datetime,
) -> tuple[ProviderRate, ...]:
    return make_complete_fiat_rates(effective_at=fixed_utc_now)


@pytest.fixture
def complete_crypto_provider_rates(
    fixed_utc_now: datetime,
) -> tuple[ProviderRate, ...]:
    return make_complete_crypto_rates(effective_at=fixed_utc_now)


@pytest.fixture
def fake_bnm_provider(
    complete_fiat_provider_rates: tuple[ProviderRate, ...],
) -> FakeBnmRateProvider:
    return FakeBnmRateProvider(latest_rates=complete_fiat_provider_rates)


@pytest.fixture
def fake_coingecko_provider(
    complete_crypto_provider_rates: tuple[ProviderRate, ...],
) -> FakeCoinGeckoRateProvider:
    return FakeCoinGeckoRateProvider(latest_rates=complete_crypto_provider_rates)


@pytest.fixture
def fake_rate_providers(
    fake_bnm_provider: FakeBnmRateProvider,
    fake_coingecko_provider: FakeCoinGeckoRateProvider,
) -> tuple[FakeBnmRateProvider, FakeCoinGeckoRateProvider]:
    return fake_bnm_provider, fake_coingecko_provider


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        database_url="mssql+pyodbc://placeholder-test-db",
        bnm_base_url="https://bnm.invalid/official_exchange_rates",
        coingecko_base_url="https://coingecko.invalid/api/v3",
        coingecko_api_key="placeholder_test_api_key",
    )


@pytest.fixture
def isolated_sqlalchemy_session() -> IsolatedSession:
    return IsolatedSession()


@pytest.fixture
def isolated_session_factory(
    isolated_sqlalchemy_session: IsolatedSession,
) -> Callable[[], IsolatedSession]:
    """Inject a callable session factory without constructing a SQLAlchemy engine."""
    return lambda: isolated_sqlalchemy_session


@pytest.fixture
def queued_result_factory() -> Callable[[Any], QueuedResult]:
    return lambda rows: QueuedResult(rows)
