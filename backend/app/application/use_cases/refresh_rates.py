"""Source-aware refresh orchestration for complete current-rate candidates."""

from collections.abc import Callable, Sequence
from datetime import UTC, date, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from app.application.services.snapshot_service import (
    AssemblyReason,
    Clock,
    RateFreshnessMetadata,
    SnapshotIdFactory,
    SnapshotService,
)
from app.domain.entities.rate_entry import RateEntry
from app.domain.entities.rate_snapshot import RateSnapshot
from app.domain.enums.currency_type import CurrencyType
from app.domain.enums.freshness_state import FreshnessState
from app.domain.interfaces.rate_provider import ProviderRate, RateProvider
from app.domain.interfaces.unit_of_work import UnitOfWork


PublicationDayResolver = Callable[[date], bool]

_MOLDOVA_TIMEZONE = ZoneInfo("Europe/Chisinau")
_CRYPTO_CURRENT_WINDOW = timedelta(minutes=15)


def weekday_publication_calendar(value: date) -> bool:
    """Return the default BNM publishing expectation for a Moldova date.

    Deployments can inject an official holiday-aware resolver. The default captures
    the stable weekend rule without embedding a year-specific holiday table.
    """

    return value.weekday() < 5


class RefreshRates:
    """Assemble one complete candidate using canonical source freshness rules."""

    def __init__(
        self,
        providers: Sequence[RateProvider],
        *,
        unit_of_work: UnitOfWork | None = None,
        clock: Clock | None = None,
        snapshot_id_factory: SnapshotIdFactory | None = None,
        is_bnm_publication_day: PublicationDayResolver | None = None,
    ) -> None:
        self._providers = tuple(providers)
        self._unit_of_work = unit_of_work
        self._clock = clock or (lambda: datetime.now(UTC))
        self._snapshot_id_factory = snapshot_id_factory
        self._is_bnm_publication_day = (
            is_bnm_publication_day or weekday_publication_calendar
        )

    async def assemble_candidate(
        self,
        *,
        previous_snapshot: RateSnapshot | None = None,
        explicit_fallback_rates: Sequence[ProviderRate] = (),
    ) -> RateSnapshot:
        """Return a complete validated candidate without persisting it."""

        candidate, _ = await self._assemble_candidate(
            previous_snapshot=previous_snapshot,
            explicit_fallback_rates=explicit_fallback_rates,
        )
        return candidate

    async def execute(self) -> "RefreshResult":
        """Atomically replace the active snapshot only with a complete candidate."""

        if self._unit_of_work is None:
            raise RuntimeError("Refresh execution requires a UnitOfWork.")
        with self._unit_of_work as uow:
            previous_snapshot = uow.rate_repository.get_latest_usable_snapshot()
            candidate, reused_previous = await self._assemble_candidate(
                previous_snapshot=previous_snapshot,
            )
            if reused_previous:
                if previous_snapshot is None:  # pragma: no cover - assembly invariant
                    raise RuntimeError("Previous rates were reused without a snapshot.")
                return RefreshResult(previous_snapshot, updated=False)
            uow.rate_repository.save_complete_snapshot(candidate)
            uow.commit()
            return RefreshResult(candidate, updated=True)

    async def _assemble_candidate(
        self,
        *,
        previous_snapshot: RateSnapshot | None,
        explicit_fallback_rates: Sequence[ProviderRate] = (),
    ) -> tuple[RateSnapshot, bool]:
        reused_previous = False
        base_policy = self._freshness_policy(previous_snapshot)

        def tracking_policy(
            rate: ProviderRate | RateEntry,
            captured_at: datetime,
            reason: AssemblyReason,
        ) -> RateFreshnessMetadata:
            nonlocal reused_previous
            if reason is AssemblyReason.PREVIOUS_SNAPSHOT_REUSE:
                reused_previous = True
            return base_policy(rate, captured_at, reason)

        service = SnapshotService(
            self._providers,
            clock=self._clock,
            snapshot_id_factory=self._snapshot_id_factory,
            freshness_policy=tracking_policy,
        )
        candidate = await service.assemble_snapshot(
            explicit_fallback_rates=explicit_fallback_rates,
            previous_snapshot=previous_snapshot,
        )
        return candidate, reused_previous

    def _freshness_policy(
        self,
        previous_snapshot: RateSnapshot | None,
    ) -> Callable[
        [ProviderRate | RateEntry, datetime, AssemblyReason],
        RateFreshnessMetadata,
    ]:
        previous_captured_at = (
            previous_snapshot.captured_at.astimezone(UTC)
            if previous_snapshot is not None
            else None
        )

        def classify(
            rate: ProviderRate | RateEntry,
            captured_at: datetime,
            reason: AssemblyReason,
        ) -> RateFreshnessMetadata:
            if reason is AssemblyReason.MDL_REFERENCE:
                return RateFreshnessMetadata(FreshnessState.LIVE, False, False)
            if reason is AssemblyReason.EXPLICIT_FALLBACK:
                return RateFreshnessMetadata(FreshnessState.FALLBACK, True, False)
            if rate.provider_type is CurrencyType.CRYPTO:
                return self._classify_crypto(
                    captured_at,
                    reason,
                    previous_captured_at,
                )
            return self._classify_fiat(rate, captured_at, reason)

        return classify

    @staticmethod
    def _classify_crypto(
        captured_at: datetime,
        reason: AssemblyReason,
        previous_captured_at: datetime | None,
    ) -> RateFreshnessMetadata:
        if reason is AssemblyReason.PROVIDER_CURRENT:
            return RateFreshnessMetadata(FreshnessState.LIVE, False, False)
        if reason is not AssemblyReason.PREVIOUS_SNAPSHOT_REUSE:
            raise ValueError(f"Unsupported crypto assembly reason: {reason!r}.")
        if previous_captured_at is None:
            raise ValueError("Crypto reuse requires a previous snapshot timestamp.")

        age = captured_at.astimezone(UTC) - previous_captured_at
        if age <= _CRYPTO_CURRENT_WINDOW:
            return RateFreshnessMetadata(FreshnessState.LIVE, False, False)
        return RateFreshnessMetadata(FreshnessState.CACHED, False, True)

    def _classify_fiat(
        self,
        rate: ProviderRate | RateEntry,
        captured_at: datetime,
        reason: AssemblyReason,
    ) -> RateFreshnessMetadata:
        current_date = captured_at.astimezone(_MOLDOVA_TIMEZONE).date()
        effective_date = rate.effective_at.astimezone(_MOLDOVA_TIMEZONE).date()
        publication_expected = self._is_bnm_publication_day(current_date)

        if effective_date < current_date and not publication_expected:
            return RateFreshnessMetadata(FreshnessState.FALLBACK, True, False)
        if reason is AssemblyReason.PREVIOUS_SNAPSHOT_REUSE:
            return RateFreshnessMetadata(
                FreshnessState.CACHED,
                False,
                effective_date < current_date and publication_expected,
            )
        if effective_date < current_date and publication_expected:
            return RateFreshnessMetadata(FreshnessState.CACHED, False, True)
        return RateFreshnessMetadata(FreshnessState.LIVE, False, False)


class RefreshResult:
    """Outcome of a refresh attempt and its active complete snapshot."""

    def __init__(self, snapshot: RateSnapshot, *, updated: bool) -> None:
        self.snapshot = snapshot
        self.updated = updated
