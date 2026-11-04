"""Asynchronous domain contract for external rate sources."""

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.domain.enums.currency_type import CurrencyType


@dataclass(frozen=True)
class ProviderRate:
    """Provider-produced rate normalized to MDL, before snapshot assembly."""

    currency: str
    normalized_rate_to_mdl: Decimal
    nominal_unit: int | None
    provider_name: str
    provider_type: CurrencyType
    effective_at: datetime


@dataclass(frozen=True)
class HistoricalProviderQuote:
    """Historical source quote that still needs a normalization bridge."""

    currency: str
    quoted_price: Decimal
    quote_currency: str
    provider_name: str
    provider_type: CurrencyType
    effective_at: datetime


class RateProvider(ABC):
    """Fetch provider data without exposing provider payload formats."""

    @abstractmethod
    async def fetch_latest_rates(self) -> Sequence[ProviderRate]:
        """Fetch the provider's latest normalized rate data."""

    @abstractmethod
    async def fetch_historical_rates(
        self,
        currency_codes: Sequence[str],
        start_at: datetime,
        end_at: datetime,
    ) -> Sequence[ProviderRate | HistoricalProviderQuote]:
        """Fetch normalized historical data or explicitly quoted source values."""

    @abstractmethod
    async def get_metadata(self) -> Mapping[str, str]:
        """Return provider metadata as domain-neutral key/value data."""
