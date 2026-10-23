"""RateSnapshot domain entity representing a consistency boundary of exchange rate entries."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from app.domain.entities.rate_entry import RateEntry


class RateSnapshotError(ValueError):
    """Raised when RateSnapshot validation fails."""


@dataclass(frozen=True)
class RateSnapshot:
    """Pure domain entity representing a validated point-in-time snapshot of rate entries."""

    snapshot_id: UUID
    captured_at: datetime
    rates: tuple[RateEntry, ...]

    def __init__(
        self,
        snapshot_id: UUID | str | None,
        captured_at: datetime,
        rates: Iterable[RateEntry],
    ) -> None:
        """Initialize and validate RateSnapshot."""
        # Validate snapshot_id
        if snapshot_id is None:
            snap_id = uuid4()
        elif isinstance(snapshot_id, str):
            try:
                snap_id = UUID(snapshot_id)
            except ValueError as exc:
                raise RateSnapshotError(f"Invalid snapshot_id UUID string: {snapshot_id!r}") from exc
        elif isinstance(snapshot_id, UUID):
            snap_id = snapshot_id
        else:
            raise RateSnapshotError(
                f"snapshot_id must be a UUID or UUID string, got {type(snapshot_id).__name__}."
            )

        # Validate captured_at (timezone-aware)
        if not isinstance(captured_at, datetime):
            raise RateSnapshotError(f"captured_at must be a datetime, got {type(captured_at).__name__}.")
        if captured_at.tzinfo is None or captured_at.tzinfo.utcoffset(captured_at) is None:
            raise RateSnapshotError("captured_at must be a timezone-aware datetime.")

        # Validate rates
        if rates is None:
            raise RateSnapshotError("RateSnapshot must contain at least one rate entry.")
        try:
            rates_tuple = tuple(rates)
        except TypeError as exc:
            raise RateSnapshotError("rates must be an iterable collection of RateEntry.") from exc

        if not rates_tuple:
            raise RateSnapshotError("RateSnapshot must contain at least one rate entry.")

        seen_currencies: set[str] = set()
        for rate in rates_tuple:
            if not isinstance(rate, RateEntry):
                raise RateSnapshotError(
                    f"All items in rates must be RateEntry instances, got {type(rate).__name__}."
                )

            # Check snapshot_id consistency
            if rate.snapshot_id != snap_id:
                raise RateSnapshotError(
                    f"RateEntry for '{rate.currency}' has snapshot_id {rate.snapshot_id}, "
                    f"which does not match RateSnapshot id {snap_id}."
                )

            # Check duplicate currency
            if rate.currency in seen_currencies:
                raise RateSnapshotError(
                    f"Duplicate currency entry '{rate.currency}' in snapshot."
                )
            seen_currencies.add(rate.currency)

        object.__setattr__(self, "snapshot_id", snap_id)
        object.__setattr__(self, "captured_at", captured_at)
        object.__setattr__(self, "rates", rates_tuple)

    def get_rate(self, currency_code: str) -> RateEntry | None:
        """Find a rate entry by its currency code."""
        normalized = currency_code.strip().upper()
        for rate in self.rates:
            if rate.currency == normalized:
                return rate
        return None

    @property
    def currencies(self) -> set[str]:
        """Return the set of currency codes present in this snapshot."""
        return {r.currency for r in self.rates}

    def __len__(self) -> int:
        return len(self.rates)

    def __iter__(self):
        return iter(self.rates)
