"""Focused tests for pair derivation and Decimal analytics."""

from datetime import UTC, datetime
from decimal import Decimal
from types import TracebackType
from uuid import uuid4

from app.application.services.analytics_service import AnalyticsService, Trend
from app.domain.entities.rate_entry import RateEntry
from app.domain.entities.rate_snapshot import RateSnapshot
from app.domain.enums.currency_type import CurrencyType
from app.domain.enums.freshness_state import FreshnessState


class StubRepository:
    def __init__(self, snapshots: tuple[RateSnapshot, ...]) -> None:
        self.snapshots = snapshots
        self.requests: list[tuple[datetime, datetime, tuple[str, ...]]] = []

    def get_historical_snapshots(
        self,
        start_at: datetime,
        end_at: datetime,
        currency_codes: tuple[str, ...],
    ) -> tuple[RateSnapshot, ...]:
        self.requests.append((start_at, end_at, currency_codes))
        return tuple(
            snapshot
            for snapshot in self.snapshots
            if start_at <= snapshot.captured_at <= end_at
        )


class StubUnitOfWork:
    def __init__(self, repository: StubRepository) -> None:
        self.rate_repository = repository

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exc_type, exc_value, traceback


def entry(
    snapshot_id,
    code: str,
    value: str,
    *,
    provider: str,
    freshness: FreshnessState = FreshnessState.LIVE,
    fallback: bool = False,
    stale: bool = False,
) -> RateEntry:
    return RateEntry(
        snapshot_id=snapshot_id,
        currency=code,
        normalized_rate_to_mdl=Decimal(value),
        provider_name=provider,
        provider_type=(
            CurrencyType.CRYPTO if code == "BTC" else CurrencyType.FIAT
        ),
        effective_at=datetime(2026, 10, 20, 8, tzinfo=UTC),
        freshness_state=freshness,
        is_fallback=fallback,
        is_stale=stale,
    )


def snapshot(
    day: int,
    usd_value: str,
    btc_value: str | None,
    *,
    hour: int = 12,
    usd_provider: str = "BNM",
    freshness: FreshnessState = FreshnessState.LIVE,
    fallback: bool = False,
    stale: bool = False,
) -> RateSnapshot:
    snapshot_id = uuid4()
    rates = [
        entry(
            snapshot_id,
            "USD",
            usd_value,
            provider=usd_provider,
            freshness=freshness,
            fallback=fallback,
            stale=stale,
        )
    ]
    if btc_value is not None:
        rates.append(
            entry(snapshot_id, "BTC", btc_value, provider="CoinGecko")
        )
    return RateSnapshot(
        snapshot_id,
        datetime(2026, 10, day, hour, tzinfo=UTC),
        rates,
    )


def service(*snapshots: RateSnapshot) -> tuple[AnalyticsService, StubRepository]:
    repository = StubRepository(tuple(snapshots))
    return (
        AnalyticsService(
            StubUnitOfWork(repository),
            clock=lambda: datetime(2026, 10, 28, 20, tzinfo=UTC),
        ),
        repository,
    )


def test_history_uses_latest_complete_snapshot_per_day_and_preserves_legs() -> None:
    analytics, repository = service(
        snapshot(27, "20", "10", hour=10),
        snapshot(27, "30", None, hour=11),
        snapshot(
            27,
            "24",
            "8",
            hour=12,
            usd_provider="Fallback BNM",
            freshness=FreshnessState.FALLBACK,
            fallback=True,
        ),
        snapshot(28, "40", "10"),
    )

    result = analytics.get_history(" usd ", "btc", 7)

    assert [point.date.isoformat() for point in result.points] == [
        "2026-10-27",
        "2026-10-28",
    ]
    assert [point.value for point in result.points] == [Decimal("3"), Decimal("4")]
    assert result.points[0].source_rate.currency == "USD"
    assert result.points[0].source_rate.provider_name == "Fallback BNM"
    assert result.points[0].source_rate.is_fallback is True
    assert result.points[0].target_rate.currency == "BTC"
    assert result.points[0].snapshot_id != result.points[1].snapshot_id
    assert repository.requests[0][2] == ("USD", "BTC")
    assert repository.requests[0][0].date().isoformat() == "2026-10-22"


def test_analytics_uses_decimal_statistics_and_independent_counts() -> None:
    analytics, _ = service(
        snapshot(
            27,
            "1",
            "4",
            freshness=FreshnessState.CACHED,
            stale=True,
        ),
        snapshot(
            28,
            "2",
            "4",
            freshness=FreshnessState.FALLBACK,
            fallback=True,
        ),
    )

    result = analytics.get_analytics("USD", "BTC", 30)

    assert [point.value for point in result.history.points] == [
        Decimal("0.25"),
        Decimal("0.5"),
    ]
    assert result.minimum == Decimal("0.25")
    assert result.maximum == Decimal("0.5")
    assert result.average == Decimal("0.375")
    assert result.absolute_change == Decimal("0.25")
    assert result.percentage_change == Decimal("100")
    assert result.trend is Trend.GROWTH
    assert result.provenance.point_count == 2
    assert result.provenance.source_providers == ("BNM",)
    assert result.provenance.target_providers == ("CoinGecko",)
    assert result.provenance.live_entry_count == 2
    assert result.provenance.fallback_state_entry_count == 1
    assert result.provenance.cached_entry_count == 1
    assert result.provenance.stale_entry_count == 1
    assert result.provenance.fallback_entry_count == 1


def test_empty_and_same_currency_results_are_explicit() -> None:
    empty_service, _ = service(snapshot(28, "2", None))
    empty = empty_service.get_analytics("USD", "BTC", 7)
    assert empty.empty is True
    assert empty.minimum is None
    assert empty.trend is None
    assert empty.provenance.point_count == 0

    same_service, repository = service(snapshot(28, "2", None))
    same = same_service.get_history("USD", "USD", 7)
    assert same.points[0].value == Decimal("1")
    assert same.points[0].source_rate is same.points[0].target_rate
    assert repository.requests[0][2] == ("USD",)


def test_period_windows_produce_distinct_7_day_and_30_day_statistics() -> None:
    analytics, _ = service(
        snapshot(1, "1", "4"),
        snapshot(22, "2", "4"),
        snapshot(28, "4", "4"),
    )

    seven_days = analytics.get_analytics("USD", "BTC", 7)
    thirty_days = analytics.get_analytics("USD", "BTC", 30)

    assert [point.date.day for point in seven_days.history.points] == [22, 28]
    assert seven_days.minimum == Decimal("0.5")
    assert seven_days.maximum == Decimal("1")
    assert seven_days.average == Decimal("0.75")
    assert seven_days.absolute_change == Decimal("0.5")
    assert seven_days.percentage_change == Decimal("100")
    assert seven_days.trend is Trend.GROWTH
    assert [point.date.day for point in thirty_days.history.points] == [1, 22, 28]
    assert thirty_days.minimum == Decimal("0.25")
    assert thirty_days.maximum == Decimal("1")
    assert thirty_days.average == Decimal("0.5833333333333333333333333333")
    assert thirty_days.absolute_change == Decimal("0.75")
    assert thirty_days.percentage_change == Decimal("300")


def test_mixed_providers_and_snapshot_date_remain_distinct_from_effective_time() -> None:
    analytics, repository = service(
        snapshot(27, "2", "4", usd_provider="BNM"),
        snapshot(
            28,
            "3",
            "4",
            usd_provider="Emergency Fiat Feed",
            freshness=FreshnessState.CACHED,
            stale=True,
        ),
    )

    result = analytics.get_analytics("USD", "BTC", 7)

    assert result.provenance.source_providers == (
        "BNM",
        "Emergency Fiat Feed",
    )
    assert result.provenance.target_providers == ("CoinGecko",)
    point = result.history.points[-1]
    assert point.date.isoformat() == "2026-10-28"
    assert point.source_rate.effective_at.isoformat() == "2026-10-20T08:00:00+00:00"
    assert point.target_rate.effective_at.isoformat() == "2026-10-20T08:00:00+00:00"
    assert point.snapshot_id == next(
        snapshot.snapshot_id
        for snapshot in repository.snapshots
        if snapshot.captured_at.day == 28
    )
    assert result.provenance.cached_entry_count == 1
    assert result.provenance.stale_entry_count == 1
    assert result.provenance.fallback_entry_count == 0
