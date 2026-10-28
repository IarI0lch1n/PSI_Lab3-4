"""Tests for configured provider construction."""

import pytest

from app.core.config.settings import Settings
from app.domain.enums.currency_type import CurrencyType
from app.domain.interfaces.rate_provider import RateProvider
from app.infrastructure.providers.bnm_rate_provider import BnmRateProvider
from app.infrastructure.providers.coingecko_rate_provider import (
    CoinGeckoRateProvider,
)
from app.infrastructure.providers.provider_factory import RateProviderFactory


def test_factory_creates_both_providers_without_fetching_rates() -> None:
    settings = Settings(
        bnm_base_url="https://bnm.invalid",
        coingecko_base_url="https://coingecko.invalid",
    )

    providers = RateProviderFactory(settings).create_all()

    assert len(providers) == 2
    assert isinstance(providers[0], BnmRateProvider)
    assert isinstance(providers[1], CoinGeckoRateProvider)
    assert all(isinstance(provider, RateProvider) for provider in providers)


def test_factory_uses_injected_provider_builders() -> None:
    class FakeProvider(RateProvider):
        async def fetch_latest_rates(self):
            return ()

        async def fetch_historical_rates(self, currency_codes, start_at, end_at):
            return ()

        async def get_metadata(self):
            return {}

    expected = FakeProvider()
    factory = RateProviderFactory(
        Settings(),
        provider_builders={
            CurrencyType.FIAT: lambda: expected,
        },
    )

    assert factory.create_for(CurrencyType.FIAT) is expected
    assert isinstance(factory.create_for(CurrencyType.CRYPTO), CoinGeckoRateProvider)


@pytest.mark.parametrize("provider_type", ["metals", None, 42])
def test_factory_rejects_unsupported_provider_types(provider_type) -> None:
    factory = RateProviderFactory(Settings())

    with pytest.raises(ValueError, match="Unsupported provider type"):
        factory.create_for(provider_type)


def test_factory_rejects_builder_returning_non_provider() -> None:
    factory = RateProviderFactory(
        Settings(),
        provider_builders={CurrencyType.FIAT: lambda: object()},
    )

    with pytest.raises(TypeError, match="did not return a RateProvider"):
        factory.create_for(CurrencyType.FIAT)
