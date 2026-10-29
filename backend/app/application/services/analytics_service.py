"""Derive historical pair points and analytics from normalized snapshots."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum
from uuid import UUID
from zoneinfo import ZoneInfo

from app.domain.entities.currency import (
    SUPPORTED_CRYPTO_CURRENCIES,
    SUPPORTED_FIAT_CURRENCIES,
)
from app.domain.entities.rate_entry import RateEntry
from app.domain.entities.rate_snapshot import RateSnapshot
from app.domain.enums.freshness_state import FreshnessState
from app.domain.interfaces.unit_of_work import UnitOfWork


Clock = Callable[[], datetime]
_MOLDOVA_TIMEZONE = ZoneInfo("Europe/Chisinau")
_SUPPORTED_CODES = set(SUPPORTED_FIAT_CURRENCIES) | set(
    SUPPORTED_CRYPTO_CURRENCIES
)


class AnalyticsInputError(ValueError):
    """Raised when a pair or period is unsupported."""


class Trend(str, Enum):
    """Direction from the first complete point to the last."""

    GROWTH = "GROWTH"
    DECLINE = "DECLINE"
    UNCHANGED = "UNCHANGED"


@dataclass(frozen=True)
class HistoricalPoint:
    """One derived pair value with both exact normalized-rate legs."""

    date: date
    value: Decimal
    snapshot_id: UUID
    source_rate: RateEntry
    target_rate: RateEntry


@dataclass(frozen=True)
class HistoryResult:
    """Ordered complete points for a requested pair and period."""

    base_currency: str
    quote_currency: str
    period_days: int
    points: tuple[HistoricalPoint, ...]

    @property
    def empty(self) -> bool:
        return not self.points


@dataclass(frozen=True)
class ProvenanceSummary:
    """Independent provider and freshness aggregates across both legs."""

    point_count: int
    source_providers: tuple[str, ...]
    target_providers: tuple[str, ...]
    live_entry_count: int
    fallback_state_entry_count: int
    cached_entry_count: int
    stale_entry_count: int
    fallback_entry_count: int


@dataclass(frozen=True)
class AnalyticsResult:
    """Decimal statistics and provenance for complete historical points."""

    history: HistoryResult
    minimum: Decimal | None
    maximum: Decimal | None
    average: Decimal | None
    absolute_change: Decimal | None
    percentage_change: Decimal | None
    trend: Trend | None
    provenance: ProvenanceSummary

    @property
    def empty(self) -> bool:
        return self.history.empty


class AnalyticsService:
    """Query normalized entries and derive pair history without pair storage."""

    def __init__(
        self,
        unit_of_work: UnitOfWork,
        *,
        clock: Clock | None = None,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._clock = clock or (lambda: datetime.now(UTC))

    def get_history(
        self,
        base_currency: object,
        quote_currency: object,
        period_days: int,
    ) -> HistoryResult:
        """Return at most one latest complete pair point per represented day."""
        base_code = self._currency_code(base_currency, "Base")
        quote_code = self._currency_code(quote_currency, "Quote")
        if period_days not in (7, 30):
            raise AnalyticsInputError("Period must be either 7 or 30 days.")

        end_at = self._now()
        end_date = end_at.astimezone(_MOLDOVA_TIMEZONE).date()
        start_date = end_date - timedelta(days=period_days - 1)
        start_at = datetime.combine(
            start_date,
            time.min,
            tzinfo=_MOLDOVA_TIMEZONE,
        )
        requested_codes = (
            (base_code,)
            if base_code == quote_code
            else (base_code, quote_code)
        )
        with self._unit_of_work as uow:
            snapshots = uow.rate_repository.get_historical_snapshots(
                start_at,
                end_at,
                requested_codes,
            )
        points = self._derive_points(snapshots, base_code, quote_code)
        return HistoryResult(base_code, quote_code, period_days, points)

    def get_analytics(
        self,
        base_currency: object,
        quote_currency: object,
        period_days: int,
    ) -> AnalyticsResult:
        """Return period statistics and independent provenance aggregates."""
        history = self.get_history(base_currency, quote_currency, period_days)
        provenance = self._summarize_provenance(history.points)
        if history.empty:
            return AnalyticsResult(
                history,
                None,
                None,
                None,
                None,
                None,
                None,
                provenance,
            )

        values = tuple(point.value for point in history.points)
        absolute_change = values[-1] - values[0]
        trend = (
            Trend.GROWTH
            if absolute_change > 0
            else Trend.DECLINE
            if absolute_change < 0
            else Trend.UNCHANGED
        )
        return AnalyticsResult(
            history=history,
            minimum=min(values),
            maximum=max(values),
            average=sum(values, Decimal(0)) / Decimal(len(values)),
            absolute_change=absolute_change,
            percentage_change=(absolute_change / values[0]) * Decimal(100),
            trend=trend,
            provenance=provenance,
        )

    @classmethod
    def _derive_points(
        cls,
        snapshots: Sequence[RateSnapshot],
        base_code: str,
        quote_code: str,
    ) -> tuple[HistoricalPoint, ...]:
        latest_by_date: dict[date, tuple[datetime, HistoricalPoint]] = {}
        for snapshot in snapshots:
            source_rate = snapshot.get_rate(base_code)
            target_rate = (
                source_rate
                if base_code == quote_code
                else snapshot.get_rate(quote_code)
            )
            if source_rate is None or target_rate is None:
                continue
            represented_date = snapshot.captured_at.astimezone(
                _MOLDOVA_TIMEZONE
            ).date()
            value = (
                Decimal(1)
                if base_code == quote_code
                else source_rate.normalized_rate_to_mdl
                / target_rate.normalized_rate_to_mdl
            )
            point = HistoricalPoint(
                represented_date,
                value,
                snapshot.snapshot_id,
                source_rate,
                target_rate,
            )
            current = latest_by_date.get(represented_date)
            if current is None or snapshot.captured_at > current[0]:
                latest_by_date[represented_date] = (snapshot.captured_at, point)
        return tuple(
            latest_by_date[point_date][1]
            for point_date in sorted(latest_by_date)
        )

    @staticmethod
    def _summarize_provenance(
        points: Sequence[HistoricalPoint],
    ) -> ProvenanceSummary:
        source_providers = sorted(
            {point.source_rate.provider_name for point in points}
        )
        target_providers = sorted(
            {point.target_rate.provider_name for point in points}
        )
        entries = [
            rate
            for point in points
            for rate in (point.source_rate, point.target_rate)
        ]
        return ProvenanceSummary(
            point_count=len(points),
            source_providers=tuple(source_providers),
            target_providers=tuple(target_providers),
            live_entry_count=sum(
                rate.freshness_state is FreshnessState.LIVE for rate in entries
            ),
            fallback_state_entry_count=sum(
                rate.freshness_state is FreshnessState.FALLBACK
                for rate in entries
            ),
            cached_entry_count=sum(
                rate.freshness_state is FreshnessState.CACHED
                for rate in entries
            ),
            stale_entry_count=sum(rate.is_stale for rate in entries),
            fallback_entry_count=sum(rate.is_fallback for rate in entries),
        )

    @staticmethod
    def _currency_code(value: object, label: str) -> str:
        if not isinstance(value, str) or value.strip().upper() not in _SUPPORTED_CODES:
            raise AnalyticsInputError(
                f"{label} currency must be a supported currency code."
            )
        return value.strip().upper()

    def _now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise AnalyticsInputError("Analytics clock must be timezone-aware.")
        return value.astimezone(UTC)
