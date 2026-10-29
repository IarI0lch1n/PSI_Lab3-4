"""Rate refresh response schemas and freshness aggregation."""

from __future__ import annotations

from uuid import UUID

from pydantic import AwareDatetime, BaseModel

from app.application.use_cases.refresh_rates import RefreshResult
from app.domain.enums.freshness_state import FreshnessState


class RefreshPrimaryFreshnessCountsResponse(BaseModel):
    """Mutually exclusive primary freshness-state counts."""

    live: int
    fallback: int
    cached: int


class RefreshFreshnessSummaryResponse(BaseModel):
    """Primary counts plus independent stale and fallback-used counts."""

    rate_entry_freshness_counts: RefreshPrimaryFreshnessCountsResponse
    stale_entry_count: int
    fallback_entry_count: int


class RefreshResponse(BaseModel):
    """Public result for one atomic refresh attempt."""

    snapshot_id: UUID
    captured_at: AwareDatetime
    updated: bool
    rate_count: int
    freshness_summary: RefreshFreshnessSummaryResponse

    @classmethod
    def from_result(cls, result: RefreshResult) -> RefreshResponse:
        snapshot = result.snapshot
        primary_counts = {
            FreshnessState.LIVE: 0,
            FreshnessState.FALLBACK: 0,
            FreshnessState.CACHED: 0,
        }
        for rate in snapshot.rates:
            primary_counts[rate.freshness_state] += 1
        return cls(
            snapshot_id=snapshot.snapshot_id,
            captured_at=snapshot.captured_at,
            updated=result.updated,
            rate_count=len(snapshot.rates),
            freshness_summary=RefreshFreshnessSummaryResponse(
                rate_entry_freshness_counts=(
                    RefreshPrimaryFreshnessCountsResponse(
                        live=primary_counts[FreshnessState.LIVE],
                        fallback=primary_counts[FreshnessState.FALLBACK],
                        cached=primary_counts[FreshnessState.CACHED],
                    )
                ),
                stale_entry_count=sum(rate.is_stale for rate in snapshot.rates),
                fallback_entry_count=sum(
                    rate.is_fallback for rate in snapshot.rates
                ),
            ),
        )
