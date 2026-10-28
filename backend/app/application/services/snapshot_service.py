"""Application service for assembling complete rate snapshots in memory."""

import asyncio
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4

from app.domain.entities.currency import (
    SUPPORTED_CRYPTO_CURRENCIES,
    SUPPORTED_FIAT_CURRENCIES,
)
from app.domain.entities.rate_entry import RateEntry
from app.domain.entities.rate_snapshot import RateSnapshot
from app.domain.enums.currency_type import CurrencyType
from app.domain.enums.freshness_state import FreshnessState
from app.domain.interfaces.rate_provider import ProviderRate, RateProvider


class SnapshotAssemblyError(ValueError):
    """Raised when a complete, structurally valid snapshot cannot be assembled."""


class AssemblyReason(str, Enum):
    """Reason a rate is included in a candidate snapshot."""

    PROVIDER_CURRENT = "provider_current"
    EXPLICIT_FALLBACK = "explicit_fallback"
    PREVIOUS_SNAPSHOT_REUSE = "previous_snapshot_reuse"
    MDL_REFERENCE = "mdl_reference"


@dataclass(frozen=True)
class RateFreshnessMetadata:
    """Freshness fields selected by an injectable source-aware policy."""

    freshness_state: FreshnessState
    is_fallback: bool
    is_stale: bool


FreshnessPolicy = Callable[
    [ProviderRate | RateEntry, datetime, AssemblyReason],
    RateFreshnessMetadata,
]
Clock = Callable[[], datetime]
SnapshotIdFactory = Callable[[], UUID]

_CANONICAL_CURRENCIES = (
    *SUPPORTED_FIAT_CURRENCIES.keys(),
    *SUPPORTED_CRYPTO_CURRENCIES.keys(),
)
_CURRENCY_TYPES = {
    **{code: CurrencyType.FIAT for code in SUPPORTED_FIAT_CURRENCIES},
    **{code: CurrencyType.CRYPTO for code in SUPPORTED_CRYPTO_CURRENCIES},
}
_MDL_PROVIDER_NAME = "CurrencyHub Reference"


class SnapshotService:
    """Collect provider rates and assemble one complete normalized snapshot."""

    def __init__(
        self,
        providers: Sequence[RateProvider],
        *,
        clock: Clock | None = None,
        snapshot_id_factory: SnapshotIdFactory | None = None,
        freshness_policy: FreshnessPolicy | None = None,
    ) -> None:
        self._providers = tuple(providers)
        self._clock = clock or (lambda: datetime.now(UTC))
        self._snapshot_id_factory = snapshot_id_factory or uuid4
        self._freshness_policy = freshness_policy or self._default_freshness_policy

    async def assemble_snapshot(
        self,
        *,
        explicit_fallback_rates: Sequence[ProviderRate] = (),
        previous_snapshot: RateSnapshot | None = None,
    ) -> RateSnapshot:
        """Build a complete snapshot, without persisting or committing it."""
        captured_at = self._captured_at()
        provider_rates, provider_errors = await self._fetch_provider_rates()
        current_rates = self._validated_rate_map(
            provider_rates,
            source="provider",
            allow_mdl=False,
        )
        fallback_rates = self._validated_rate_map(
            explicit_fallback_rates,
            source="explicit fallback",
            allow_mdl=False,
        )

        selected: dict[str, tuple[ProviderRate | RateEntry, AssemblyReason]] = {
            **{
                code: (rate, AssemblyReason.PROVIDER_CURRENT)
                for code, rate in current_rates.items()
            },
            **{
                code: (rate, AssemblyReason.EXPLICIT_FALLBACK)
                for code, rate in fallback_rates.items()
                if code not in current_rates
            },
        }

        missing_codes = set(_CANONICAL_CURRENCIES) - set(selected) - {"MDL"}
        previous_rates: dict[str, RateEntry] = {}
        if missing_codes and previous_snapshot is not None:
            try:
                previous_rates = self._validate_previous_snapshot(previous_snapshot)
            except SnapshotAssemblyError as exc:
                self._raise_incomplete(
                    missing_codes,
                    provider_errors,
                    reason=f"previous snapshot is unusable: {exc}",
                )
            for code in missing_codes:
                previous_rate = previous_rates.get(code)
                if previous_rate is not None:
                    selected[code] = (
                        previous_rate,
                        AssemblyReason.PREVIOUS_SNAPSHOT_REUSE,
                    )

        missing_codes = set(_CANONICAL_CURRENCIES) - set(selected) - {"MDL"}
        if missing_codes:
            self._raise_incomplete(missing_codes, provider_errors)

        snapshot_id = self._snapshot_id_factory()
        mdl_rate = ProviderRate(
            currency="MDL",
            normalized_rate_to_mdl=Decimal("1"),
            nominal_unit=1,
            provider_name=_MDL_PROVIDER_NAME,
            provider_type=CurrencyType.FIAT,
            effective_at=captured_at,
        )
        selected["MDL"] = (mdl_rate, AssemblyReason.MDL_REFERENCE)

        rates = tuple(
            self._to_entry(
                selected[code][0],
                snapshot_id=snapshot_id,
                captured_at=captured_at,
                reason=selected[code][1],
            )
            for code in _CANONICAL_CURRENCIES
        )
        self._validate_final_rates(rates, snapshot_id)
        return RateSnapshot(snapshot_id, captured_at, rates)

    def _captured_at(self) -> datetime:
        captured_at = self._clock()
        if not self._is_aware(captured_at):
            raise SnapshotAssemblyError("Snapshot clock must return an aware datetime.")
        return captured_at.astimezone(UTC)

    async def _fetch_provider_rates(
        self,
    ) -> tuple[list[ProviderRate], list[Exception]]:
        if not self._providers:
            return [], []
        results = await asyncio.gather(
            *(provider.fetch_latest_rates() for provider in self._providers),
            return_exceptions=True,
        )
        rates: list[ProviderRate] = []
        errors: list[Exception] = []
        for result in results:
            if isinstance(result, asyncio.CancelledError):
                raise result
            if isinstance(result, Exception):
                errors.append(result)
                continue
            if isinstance(result, (str, bytes)) or not isinstance(result, Sequence):
                raise SnapshotAssemblyError(
                    "Rate provider must return a sequence of ProviderRate values."
                )
            if any(not isinstance(rate, ProviderRate) for rate in result):
                raise SnapshotAssemblyError(
                    "Rate provider returned a value that is not a ProviderRate."
                )
            rates.extend(result)
        return rates, errors

    @classmethod
    def _validated_rate_map(
        cls,
        rates: Sequence[ProviderRate],
        *,
        source: str,
        allow_mdl: bool,
    ) -> dict[str, ProviderRate]:
        result: dict[str, ProviderRate] = {}
        for rate in rates:
            if not isinstance(rate, ProviderRate):
                raise SnapshotAssemblyError(
                    f"{source} input contains a value that is not a ProviderRate."
                )
            normalized_rate = cls._validate_provider_rate(rate, source=source)
            code = normalized_rate.currency
            if code == "MDL" and not allow_mdl:
                raise SnapshotAssemblyError(
                    f"{source} data must not supply the internal MDL reference."
                )
            if code in result:
                raise SnapshotAssemblyError(
                    f"{source} data contains duplicate currency {code}."
                )
            result[code] = normalized_rate
        return result

    @classmethod
    def _validate_provider_rate(
        cls,
        rate: ProviderRate,
        *,
        source: str,
    ) -> ProviderRate:
        if not isinstance(rate.currency, str) or not rate.currency.strip():
            raise SnapshotAssemblyError(f"{source} rate has an empty currency code.")
        code = rate.currency.strip().upper()
        expected_type = _CURRENCY_TYPES.get(code)
        if expected_type is None:
            raise SnapshotAssemblyError(
                f"{source} rate contains unsupported currency {code}."
            )
        if rate.provider_type is not expected_type:
            raise SnapshotAssemblyError(
                f"{source} rate for {code} has an invalid provider type."
            )
        cls._validate_rate_fields(
            code=code,
            value=rate.normalized_rate_to_mdl,
            nominal_unit=rate.nominal_unit,
            provider_name=rate.provider_name,
            provider_type=rate.provider_type,
            effective_at=rate.effective_at,
            source=source,
        )
        return ProviderRate(
            currency=code,
            normalized_rate_to_mdl=rate.normalized_rate_to_mdl,
            nominal_unit=rate.nominal_unit,
            provider_name=rate.provider_name,
            provider_type=rate.provider_type,
            effective_at=rate.effective_at,
        )

    @classmethod
    def _validate_previous_snapshot(
        cls,
        snapshot: RateSnapshot,
    ) -> dict[str, RateEntry]:
        if not isinstance(snapshot, RateSnapshot):
            raise SnapshotAssemblyError("Previous snapshot is not a RateSnapshot.")
        if not cls._is_aware(snapshot.captured_at):
            raise SnapshotAssemblyError(
                "Previous snapshot captured_at must be timezone-aware."
            )

        entries: dict[str, RateEntry] = {}
        for entry in snapshot.rates:
            if not isinstance(entry, RateEntry):
                raise SnapshotAssemblyError(
                    "Previous snapshot contains a non-RateEntry value."
                )
            code = entry.currency.strip().upper()
            if code not in _CURRENCY_TYPES:
                raise SnapshotAssemblyError(
                    f"Previous snapshot contains unsupported currency {code}."
                )
            if code in entries:
                raise SnapshotAssemblyError(
                    f"Previous snapshot contains duplicate currency {code}."
                )
            if entry.snapshot_id != snapshot.snapshot_id:
                raise SnapshotAssemblyError(
                    f"Previous snapshot entry {code} has an inconsistent snapshot_id."
                )
            expected_type = _CURRENCY_TYPES[code]
            if entry.provider_type is not expected_type:
                raise SnapshotAssemblyError(
                    f"Previous snapshot entry {code} has an invalid provider type."
                )
            cls._validate_rate_fields(
                code=code,
                value=entry.normalized_rate_to_mdl,
                nominal_unit=entry.nominal_unit,
                provider_name=entry.provider_name,
                provider_type=entry.provider_type,
                effective_at=entry.effective_at,
                source="previous snapshot",
            )
            if code == "MDL" and (
                entry.normalized_rate_to_mdl != Decimal("1")
                or entry.nominal_unit != 1
            ):
                raise SnapshotAssemblyError(
                    "Previous snapshot MDL reference must have a normalized rate "
                    "of Decimal('1') and nominal_unit of 1."
                )
            entries[code] = entry

        missing_codes = set(_CANONICAL_CURRENCIES) - set(entries)
        if missing_codes:
            raise SnapshotAssemblyError(
                "Previous snapshot is missing required currencies: "
                f"{', '.join(sorted(missing_codes))}."
            )
        return entries

    @classmethod
    def _validate_rate_fields(
        cls,
        *,
        code: str,
        value: Decimal,
        nominal_unit: int | None,
        provider_name: str,
        provider_type: CurrencyType,
        effective_at: datetime,
        source: str,
    ) -> None:
        if not isinstance(value, Decimal) or not value.is_finite() or value <= 0:
            raise SnapshotAssemblyError(
                f"{source} rate for {code} must be a positive finite Decimal."
            )
        if nominal_unit is not None and (
            isinstance(nominal_unit, bool)
            or not isinstance(nominal_unit, int)
            or nominal_unit <= 0
        ):
            raise SnapshotAssemblyError(
                f"{source} rate for {code} has an invalid nominal_unit."
            )
        if not isinstance(provider_name, str) or not provider_name.strip():
            raise SnapshotAssemblyError(
                f"{source} rate for {code} has an empty provider_name."
            )
        if not isinstance(provider_type, CurrencyType):
            raise SnapshotAssemblyError(
                f"{source} rate for {code} has an invalid provider_type."
            )
        if not isinstance(effective_at, datetime) or not cls._is_aware(effective_at):
            raise SnapshotAssemblyError(
                f"{source} rate for {code} must have a timezone-aware effective_at."
            )

    def _to_entry(
        self,
        rate: ProviderRate | RateEntry,
        *,
        snapshot_id: UUID,
        captured_at: datetime,
        reason: AssemblyReason,
    ) -> RateEntry:
        metadata = self._freshness_policy(rate, captured_at, reason)
        if not isinstance(metadata, RateFreshnessMetadata):
            raise SnapshotAssemblyError(
                "Freshness policy must return RateFreshnessMetadata."
            )
        if not isinstance(metadata.freshness_state, FreshnessState):
            raise SnapshotAssemblyError(
                "Freshness policy returned an invalid freshness_state."
            )
        if not isinstance(metadata.is_fallback, bool) or not isinstance(
            metadata.is_stale, bool
        ):
            raise SnapshotAssemblyError(
                "Freshness policy must return boolean fallback and stale flags."
            )
        if reason is AssemblyReason.EXPLICIT_FALLBACK and (
            metadata.freshness_state is not FreshnessState.FALLBACK
            or not metadata.is_fallback
        ):
            raise SnapshotAssemblyError(
                "Explicit fallback rates must remain marked as fallback."
            )
        return RateEntry(
            snapshot_id=snapshot_id,
            currency=rate.currency,
            normalized_rate_to_mdl=rate.normalized_rate_to_mdl,
            nominal_unit=rate.nominal_unit,
            provider_name=rate.provider_name,
            provider_type=rate.provider_type,
            effective_at=rate.effective_at,
            freshness_state=metadata.freshness_state,
            is_fallback=metadata.is_fallback,
            is_stale=metadata.is_stale,
        )

    @staticmethod
    def _default_freshness_policy(
        rate: ProviderRate | RateEntry,
        captured_at: datetime,
        reason: AssemblyReason,
    ) -> RateFreshnessMetadata:
        """Classify assembly source only; source-specific age rules belong to T052."""
        del captured_at
        if reason in (AssemblyReason.PROVIDER_CURRENT, AssemblyReason.MDL_REFERENCE):
            return RateFreshnessMetadata(FreshnessState.LIVE, False, False)
        if reason is AssemblyReason.EXPLICIT_FALLBACK:
            return RateFreshnessMetadata(FreshnessState.FALLBACK, True, False)
        if reason is AssemblyReason.PREVIOUS_SNAPSHOT_REUSE:
            is_fallback = rate.is_fallback if isinstance(rate, RateEntry) else False
            return RateFreshnessMetadata(FreshnessState.CACHED, is_fallback, False)
        raise SnapshotAssemblyError(f"Unsupported assembly reason: {reason!r}.")

    @classmethod
    def _validate_final_rates(
        cls,
        rates: Sequence[RateEntry],
        snapshot_id: UUID,
    ) -> None:
        if len(rates) != len(_CANONICAL_CURRENCIES):
            raise SnapshotAssemblyError(
                "Assembled snapshot does not contain exactly 18 currencies."
            )
        if tuple(rate.currency for rate in rates) != _CANONICAL_CURRENCIES:
            raise SnapshotAssemblyError(
                "Assembled snapshot currencies are not in canonical order."
            )
        for rate in rates:
            if rate.snapshot_id != snapshot_id:
                raise SnapshotAssemblyError(
                    f"Rate entry {rate.currency} has inconsistent snapshot_id."
                )

    @staticmethod
    def _is_aware(value: datetime) -> bool:
        return value.tzinfo is not None and value.tzinfo.utcoffset(value) is not None

    @staticmethod
    def _raise_incomplete(
        missing_codes: set[str],
        provider_errors: Sequence[Exception],
        reason: str | None = None,
    ) -> None:
        message = (
            "Cannot assemble complete snapshot; missing currencies: "
            f"{', '.join(sorted(missing_codes))}."
        )
        if reason:
            message = f"{message} {reason}"
        error = SnapshotAssemblyError(message)
        if provider_errors:
            raise error from provider_errors[0]
        raise error
