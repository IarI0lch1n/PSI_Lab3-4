"""Latest-rate response schemas and domain mappings."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel

from app.domain.entities.rate_entry import RateEntry
from app.domain.entities.rate_snapshot import RateSnapshot
from app.domain.enums.currency_type import CurrencyType
from app.domain.enums.freshness_state import FreshnessState


class RateEntryResponse(BaseModel):
    """Public representation of one rate and its independent provenance."""

    currency: str
    normalized_rate_to_mdl: str
    nominal_unit: int
    provider_name: str
    provider_type: CurrencyType
    effective_at: AwareDatetime
    freshness_state: FreshnessState
    is_fallback: bool
    is_stale: bool

    @classmethod
    def from_domain(cls, rate: RateEntry) -> RateEntryResponse:
        """Map a rate entry without changing its value or provenance."""
        normalized_rate = rate.normalized_rate_to_mdl
        if not isinstance(normalized_rate, Decimal):
            raise TypeError("normalized_rate_to_mdl must be a Decimal.")
        return cls(
            currency=rate.currency,
            normalized_rate_to_mdl=format(normalized_rate, "f"),
            nominal_unit=rate.nominal_unit,
            provider_name=rate.provider_name,
            provider_type=rate.provider_type,
            effective_at=rate.effective_at,
            freshness_state=rate.freshness_state,
            is_fallback=rate.is_fallback,
            is_stale=rate.is_stale,
        )


class RateSnapshotResponse(BaseModel):
    """Public representation of a snapshot with per-entry rate context."""

    snapshot_id: UUID
    captured_at: AwareDatetime
    rates: list[RateEntryResponse]

    @classmethod
    def from_domain(cls, snapshot: RateSnapshot) -> RateSnapshotResponse:
        """Map a snapshot while retaining each entry's original context."""
        return cls(
            snapshot_id=snapshot.snapshot_id,
            captured_at=snapshot.captured_at,
            rates=[RateEntryResponse.from_domain(rate) for rate in snapshot.rates],
        )
