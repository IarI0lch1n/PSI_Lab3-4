"""Factory for constructing configured infrastructure rate providers."""

from collections.abc import Callable, Mapping

from app.core.config.settings import Settings, get_settings
from app.domain.enums.currency_type import CurrencyType
from app.domain.interfaces.rate_provider import RateProvider
from app.infrastructure.providers.bnm_rate_provider import BnmRateProvider
from app.infrastructure.providers.coingecko_rate_provider import (
    CoinGeckoRateProvider,
)


ProviderBuilder = Callable[[], RateProvider]


class RateProviderFactory:
    """Construct provider adapters without performing provider network calls."""

    def __init__(
        self,
        settings: Settings | None = None,
        provider_builders: Mapping[CurrencyType, ProviderBuilder] | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._provider_builders = dict(provider_builders or {})

    def create_for(self, provider_type: CurrencyType) -> RateProvider:
        """Create the configured provider for a supported currency type."""
        try:
            normalized_type = (
                provider_type
                if isinstance(provider_type, CurrencyType)
                else CurrencyType(provider_type)
            )
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Unsupported provider type: {provider_type!r}.") from exc

        builder = self._provider_builders.get(normalized_type)
        if builder is not None:
            provider = builder()
            if not isinstance(provider, RateProvider):
                raise TypeError(
                    f"Provider builder for {normalized_type.value} did not return "
                    "a RateProvider."
                )
            return provider

        if normalized_type is CurrencyType.FIAT:
            return BnmRateProvider(settings=self._settings)
        if normalized_type is CurrencyType.CRYPTO:
            return CoinGeckoRateProvider(settings=self._settings)
        raise ValueError(f"Unsupported provider type: {normalized_type!r}.")

    def create_all(self) -> tuple[RateProvider, ...]:
        """Create one provider for every supported provider type."""
        return (
            self.create_for(CurrencyType.FIAT),
            self.create_for(CurrencyType.CRYPTO),
        )
