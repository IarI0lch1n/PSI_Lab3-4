"""First-run bootstrap of complete daily normalized-rate snapshots."""

import asyncio
from collections.abc import Callable, Sequence
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from app.domain.entities.currency import (
    SUPPORTED_CRYPTO_CURRENCIES,
    SUPPORTED_FIAT_CURRENCIES,
)
from app.domain.entities.rate_entry import RateEntry
from app.domain.entities.rate_snapshot import RateSnapshot
from app.domain.enums.currency_type import CurrencyType
from app.domain.enums.freshness_state import FreshnessState
from app.domain.interfaces.rate_provider import ProviderRate, RateProvider
from app.domain.interfaces.unit_of_work import UnitOfWork


Clock = Callable[[], datetime]
SnapshotIdFactory = Callable[[], UUID]
_MOLDOVA_TIMEZONE = ZoneInfo("Europe/Chisinau")
_FIAT_CODES = tuple(SUPPORTED_FIAT_CURRENCIES)
_CRYPTO_CODES = tuple(SUPPORTED_CRYPTO_CURRENCIES)
_CANONICAL_CODES = (*_FIAT_CODES, *_CRYPTO_CODES)
_PROVIDER_CODES = tuple(code for code in _CANONICAL_CODES if code != "MDL")


class BootstrapHistoryError(ValueError):
    """Raised when historical provider data is structurally invalid."""


class BootstrapHistory:
    """Persist up to 30 complete historical daily snapshots on first run."""

    def __init__(
        self,
        providers: Sequence[RateProvider],
        unit_of_work: UnitOfWork,
        *,
        clock: Clock | None = None,
        snapshot_id_factory: SnapshotIdFactory | None = None,
    ) -> None:
        self._providers = tuple(providers)
        self._unit_of_work = unit_of_work
        self._clock = clock or (lambda: datetime.now(UTC))
        self._snapshot_id_factory = snapshot_id_factory or uuid4

    async def execute(self) -> tuple[RateSnapshot, ...]:
        """Bootstrap once, returning the snapshots persisted by this call."""
        end_at = self._aware_utc_now()
        end_date = end_at.astimezone(_MOLDOVA_TIMEZONE).date()
        start_date = end_date - timedelta(days=29)
        start_at = datetime.combine(
            start_date,
            time.min,
            tzinfo=_MOLDOVA_TIMEZONE,
        )

        with self._unit_of_work as uow:
            existing = uow.rate_repository.get_historical_snapshots(
                start_at,
                end_at,
            )
            if existing:
                return ()

            provider_rates = await self._fetch_history(start_at, end_at)
            snapshots = self._build_snapshots(
                provider_rates,
                start_date,
                end_date,
            )
            for snapshot in snapshots:
                uow.rate_repository.save_complete_snapshot(snapshot)
            if snapshots:
                uow.commit()
            return snapshots

    async def _fetch_history(
        self,
        start_at: datetime,
        end_at: datetime,
    ) -> tuple[ProviderRate, ...]:
        results = await asyncio.gather(
            *(
                provider.fetch_historical_rates(
                    _PROVIDER_CODES,
                    start_at,
                    end_at,
                )
                for provider in self._providers
            )
        )
        rates: list[ProviderRate] = []
        for result in results:
            if isinstance(result, (str, bytes)) or not isinstance(result, Sequence):
                raise BootstrapHistoryError(
                    "Historical provider must return ProviderRate values."
                )
            if any(not isinstance(rate, ProviderRate) for rate in result):
                raise BootstrapHistoryError(
                    "Historical provider returned a non-ProviderRate value."
                )
            rates.extend(result)
        return tuple(rates)

    def _build_snapshots(
        self,
        rates: Sequence[ProviderRate],
        start_date: date,
        end_date: date,
    ) -> tuple[RateSnapshot, ...]:
        rates_by_code: dict[str, list[ProviderRate]] = {
            code: [] for code in _PROVIDER_CODES
        }
        seen: set[tuple[str, datetime]] = set()
        for rate in rates:
            code = rate.currency.strip().upper()
            if code not in rates_by_code:
                raise BootstrapHistoryError(
                    f"Historical provider returned unsupported currency {code}."
                )
            key = (code, rate.effective_at)
            if key in seen:
                raise BootstrapHistoryError(
                    f"Historical provider returned duplicate {code} timestamp."
                )
            seen.add(key)
            rates_by_code[code].append(rate)

        for code_rates in rates_by_code.values():
            code_rates.sort(key=lambda rate: rate.effective_at)

        snapshots: list[RateSnapshot] = []
        represented_date = start_date
        while represented_date <= end_date:
            selected: dict[str, ProviderRate] = {}
            for code in _PROVIDER_CODES:
                candidates = [
                    rate
                    for rate in rates_by_code[code]
                    if self._local_date(rate.effective_at) <= represented_date
                    and (
                        code in _FIAT_CODES
                        or self._local_date(rate.effective_at) == represented_date
                    )
                ]
                if candidates:
                    selected[code] = candidates[-1]
            if len(selected) == len(_PROVIDER_CODES):
                snapshots.append(
                    self._build_snapshot(represented_date, selected)
                )
            represented_date += timedelta(days=1)
        return tuple(snapshots)

    def _build_snapshot(
        self,
        represented_date: date,
        selected: dict[str, ProviderRate],
    ) -> RateSnapshot:
        snapshot_id = self._snapshot_id_factory()
        captured_at = max(
            rate.effective_at.astimezone(UTC) for rate in selected.values()
        )
        entries: list[RateEntry] = []
        for code in _PROVIDER_CODES:
            rate = selected[code]
            is_fallback = (
                code in _FIAT_CODES
                and self._local_date(rate.effective_at) < represented_date
            )
            entries.append(
                RateEntry(
                    snapshot_id=snapshot_id,
                    currency=code,
                    normalized_rate_to_mdl=rate.normalized_rate_to_mdl,
                    nominal_unit=rate.nominal_unit,
                    provider_name=rate.provider_name,
                    provider_type=rate.provider_type,
                    effective_at=rate.effective_at,
                    freshness_state=(
                        FreshnessState.FALLBACK
                        if is_fallback
                        else FreshnessState.LIVE
                    ),
                    is_fallback=is_fallback,
                    is_stale=False,
                )
            )
        entries.insert(
            _FIAT_CODES.index("MDL"),
            RateEntry(
                snapshot_id=snapshot_id,
                currency="MDL",
                normalized_rate_to_mdl=Decimal("1"),
                nominal_unit=1,
                provider_name="CurrencyHub Reference",
                provider_type=CurrencyType.FIAT,
                effective_at=captured_at,
                freshness_state=FreshnessState.LIVE,
                is_fallback=False,
                is_stale=False,
            ),
        )
        if tuple(entry.currency for entry in entries) != _CANONICAL_CODES:
            raise BootstrapHistoryError(
                "Historical snapshot currencies are not in canonical order."
            )
        return RateSnapshot(snapshot_id, captured_at, entries)

    def _aware_utc_now(self) -> datetime:
        now = self._clock()
        if now.tzinfo is None or now.utcoffset() is None:
            raise BootstrapHistoryError("Bootstrap clock must be timezone-aware.")
        return now.astimezone(UTC)

    @staticmethod
    def _local_date(value: datetime) -> date:
        if value.tzinfo is None or value.utcoffset() is None:
            raise BootstrapHistoryError(
                "Historical provider timestamps must be timezone-aware."
            )
        return value.astimezone(_MOLDOVA_TIMEZONE).date()
