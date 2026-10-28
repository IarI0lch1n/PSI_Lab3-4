"""Reusable deterministic fake providers and isolated SQLAlchemy test doubles."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from app.domain.entities.currency import (
    SUPPORTED_CRYPTO_CURRENCIES,
    SUPPORTED_FIAT_CURRENCIES,
)
from app.domain.enums.currency_type import CurrencyType
from app.domain.interfaces.rate_provider import ProviderRate, RateProvider


FIXED_UTC_NOW = datetime(2026, 10, 28, 8, 0, tzinfo=UTC)
_FIAT_CODES = tuple(
    code for code in SUPPORTED_FIAT_CURRENCIES if code != "MDL"
)
_CRYPTO_CODES = tuple(SUPPORTED_CRYPTO_CURRENCIES)


@dataclass(frozen=True)
class HistoricalRateRequest:
    """Recorded arguments from one fake historical provider call."""

    currency_codes: tuple[str, ...]
    start_at: datetime
    end_at: datetime


def make_provider_rate(
    currency: str,
    normalized_rate_to_mdl: Decimal,
    *,
    provider_name: str | None = None,
    provider_type: CurrencyType | None = None,
    effective_at: datetime = FIXED_UTC_NOW,
    nominal_unit: int | None = 1,
) -> ProviderRate:
    """Create one validated-for-fixtures ProviderRate without float conversion."""
    if not isinstance(normalized_rate_to_mdl, Decimal):
        raise TypeError("normalized_rate_to_mdl must be a Decimal.")
    if effective_at.tzinfo is None or effective_at.utcoffset() is None:
        raise ValueError("effective_at must be timezone-aware.")

    code = currency.strip().upper()
    if provider_type is None:
        if code in SUPPORTED_FIAT_CURRENCIES:
            provider_type = CurrencyType.FIAT
        elif code in SUPPORTED_CRYPTO_CURRENCIES:
            provider_type = CurrencyType.CRYPTO
        else:
            raise ValueError(f"Unsupported fixture currency: {currency!r}.")

    if provider_name is None:
        provider_name = (
            "Fake BNM"
            if provider_type is CurrencyType.FIAT
            else "Fake CoinGecko"
        )
    return ProviderRate(
        currency=code,
        normalized_rate_to_mdl=normalized_rate_to_mdl,
        nominal_unit=nominal_unit,
        provider_name=provider_name,
        provider_type=provider_type,
        effective_at=effective_at,
    )


def make_complete_fiat_rates(
    *,
    effective_at: datetime = FIXED_UTC_NOW,
) -> tuple[ProviderRate, ...]:
    """Create canonical non-MDL fiat rates for a fake BNM provider."""
    return tuple(
        make_provider_rate(
            code,
            Decimal(index),
            provider_name="Fake BNM",
            provider_type=CurrencyType.FIAT,
            effective_at=effective_at,
        )
        for index, code in enumerate(_FIAT_CODES, start=1)
    )


def make_complete_crypto_rates(
    *,
    effective_at: datetime = FIXED_UTC_NOW,
) -> tuple[ProviderRate, ...]:
    """Create all canonical crypto rates for a fake CoinGecko provider."""
    return tuple(
        make_provider_rate(
            code,
            Decimal(index),
            provider_name="Fake CoinGecko",
            provider_type=CurrencyType.CRYPTO,
            effective_at=effective_at,
        )
        for index, code in enumerate(_CRYPTO_CODES, start=1)
    )


class FakeRateProvider(RateProvider):
    """Configurable RateProvider fake that performs no networking or parsing."""

    def __init__(
        self,
        *,
        latest_rates: Sequence[ProviderRate] = (),
        latest_error: Exception | None = None,
        historical_rates: Sequence[ProviderRate] = (),
        historical_error: Exception | None = None,
        metadata: Mapping[str, str] | None = None,
        provider_name: str = "Fake Rate Provider",
        provider_type: CurrencyType = CurrencyType.FIAT,
    ) -> None:
        self._latest_rates = tuple(latest_rates)
        self.latest_error = latest_error
        self._historical_rates = tuple(historical_rates)
        self.historical_error = historical_error
        self._metadata = dict(
            metadata
            or {
                "provider_name": provider_name,
                "provider_type": provider_type.value,
            }
        )
        self.provider_name = provider_name
        self.provider_type = provider_type
        self.latest_call_count = 0
        self.historical_call_count = 0
        self.historical_requests: list[HistoricalRateRequest] = []

    async def fetch_latest_rates(self) -> Sequence[ProviderRate]:
        self.latest_call_count += 1
        if self.latest_error is not None:
            raise self.latest_error
        return self._latest_rates

    async def fetch_historical_rates(
        self,
        currency_codes: Sequence[str],
        start_at: datetime,
        end_at: datetime,
    ) -> Sequence[ProviderRate]:
        self.historical_call_count += 1
        self.historical_requests.append(
            HistoricalRateRequest(tuple(currency_codes), start_at, end_at)
        )
        if self.historical_error is not None:
            raise self.historical_error
        return self._historical_rates

    async def get_metadata(self) -> Mapping[str, str]:
        return dict(self._metadata)


class FakeBnmRateProvider(FakeRateProvider):
    """Fake fiat provider with stable BNM test identity."""

    def __init__(
        self,
        *,
        latest_rates: Sequence[ProviderRate] = (),
        latest_error: Exception | None = None,
        historical_rates: Sequence[ProviderRate] = (),
        historical_error: Exception | None = None,
        metadata: Mapping[str, str] | None = None,
    ) -> None:
        super().__init__(
            latest_rates=latest_rates,
            latest_error=latest_error,
            historical_rates=historical_rates,
            historical_error=historical_error,
            metadata=metadata
            or {"provider_name": "Fake BNM", "provider_type": "fiat"},
            provider_name="Fake BNM",
            provider_type=CurrencyType.FIAT,
        )


class FakeCoinGeckoRateProvider(FakeRateProvider):
    """Fake crypto provider with stable CoinGecko test identity."""

    def __init__(
        self,
        *,
        latest_rates: Sequence[ProviderRate] = (),
        latest_error: Exception | None = None,
        historical_rates: Sequence[ProviderRate] = (),
        historical_error: Exception | None = None,
        metadata: Mapping[str, str] | None = None,
    ) -> None:
        super().__init__(
            latest_rates=latest_rates,
            latest_error=latest_error,
            historical_rates=historical_rates,
            historical_error=historical_error,
            metadata=metadata
            or {
                "provider_name": "Fake CoinGecko",
                "provider_type": "crypto",
            },
            provider_name="Fake CoinGecko",
            provider_type=CurrencyType.CRYPTO,
        )


class QueuedScalars:
    """Small scalar-result double compatible with repository query usage."""

    def __init__(self, rows: Sequence[object]) -> None:
        self._rows = list(rows)

    def all(self) -> list[object]:
        return self._rows

    def first(self) -> object | None:
        return self._rows[0] if self._rows else None


class QueuedResult:
    """Queued execute result supporting scalar and row retrieval."""

    def __init__(self, rows: Sequence[object]) -> None:
        self._rows = list(rows)

    def scalars(self) -> QueuedScalars:
        return QueuedScalars(self._rows)

    def all(self) -> list[object]:
        return self._rows


class IsolatedSession:
    """Session-compatible repository test double that never creates an engine."""

    def __init__(self, results: Sequence[QueuedResult] = ()) -> None:
        self.results = list(results)
        self.statements: list[object] = []
        self.added: list[object] = []
        self.added_all: list[object] = []
        self.flush_calls = 0
        self.commit_calls = 0
        self.rollback_calls = 0
        self.close_calls = 0
        self.existing: object | None = None

    def execute(self, statement: object) -> QueuedResult:
        self.statements.append(statement)
        if not self.results:
            raise AssertionError("IsolatedSession has no queued execute result.")
        return self.results.pop(0)

    def get(self, model: type[object], identity: object) -> object | None:
        del model, identity
        return self.existing

    def add(self, instance: object) -> None:
        self.added.append(instance)

    def add_all(self, instances: Sequence[object]) -> None:
        self.added_all.extend(instances)

    def flush(self) -> None:
        self.flush_calls += 1

    def commit(self) -> None:
        self.commit_calls += 1

    def rollback(self) -> None:
        self.rollback_calls += 1

    def close(self) -> None:
        self.close_calls += 1
