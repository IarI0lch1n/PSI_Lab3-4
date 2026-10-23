"""Asynchronous domain contract for external rate sources."""

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.domain.enums.currency_type import CurrencyType


@dataclass(frozen=True)
class ProviderRate:
    """Provider-produced normalized rate data, before snapshot assembly."""

    currency: str
    normalized_rate_to_mdl: Decimal
    nominal_unit: int | None
    provider_name: str
    provider_type: CurrencyType
    effective_at: datetime


class RateProvider(ABC):
    """Fetch normalized provider results without exposing provider payload formats."""

    @abstractmethod
    async def fetch_latest_rates(self) -> Sequence[ProviderRate]:
        """Fetch the provider's latest normalized rate data."""

    @abstractmethod
    async def fetch_historical_rates(
        self,
        currency_codes: Sequence[str],
        start_at: datetime,
        end_at: datetime,
    ) -> Sequence[ProviderRate]:
        """Fetch normalized rate data within an effective-time window."""

    @abstractmethod
    async def get_metadata(self) -> Mapping[str, str]:
        """Return provider metadata as domain-neutral key/value data."""
