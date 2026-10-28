"""Request and response schemas for currency conversion."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, StrictStr

from app.application.use_cases.convert_currency import ConversionResult
from app.domain.entities.rate_entry import RateEntry
from app.domain.enums.freshness_state import FreshnessState


class ConversionRequest(BaseModel):
    """Public conversion request with the amount preserved as submitted text."""

    model_config = ConfigDict(extra="forbid")

    amount: StrictStr
    source_currency: StrictStr
    target_currency: StrictStr


class ConversionRateLegResponse(BaseModel):
    """Provenance for one currency rate used in a conversion."""

    currency: str
    provider_name: str
    effective_at: AwareDatetime
    freshness_state: FreshnessState
    is_fallback: bool
    is_stale: bool

    @classmethod
    def from_domain(cls, rate: RateEntry) -> ConversionRateLegResponse:
        """Map one original rate entry without recalculating its provenance."""
        return cls(
            currency=rate.currency,
            provider_name=rate.provider_name,
            effective_at=rate.effective_at,
            freshness_state=rate.freshness_state,
            is_fallback=rate.is_fallback,
            is_stale=rate.is_stale,
        )


class ConversionRateContextResponse(BaseModel):
    """Independent source and target rate context and their common snapshot."""

    source_rate: ConversionRateLegResponse
    target_rate: ConversionRateLegResponse
    snapshot_id: UUID


class ConversionResponse(BaseModel):
    """Public conversion result with Decimal values serialized as exact strings."""

    source_amount: str
    converted_amount: str
    source_currency: str
    target_currency: str
    rate_value: str
    rate_context: ConversionRateContextResponse

    @classmethod
    def from_domain(cls, result: ConversionResult) -> ConversionResponse:
        """Map a domain result, preserving Decimal values and both rate entries."""
        return cls(
            source_amount=_decimal_string(result.source_amount),
            converted_amount=_decimal_string(result.converted_amount),
            source_currency=result.source_currency,
            target_currency=result.target_currency,
            rate_value=_decimal_string(result.rate_value),
            rate_context=ConversionRateContextResponse(
                source_rate=ConversionRateLegResponse.from_domain(
                    result.source_rate
                ),
                target_rate=ConversionRateLegResponse.from_domain(
                    result.target_rate
                ),
                snapshot_id=result.snapshot_id,
            ),
        )


def _decimal_string(value: Decimal) -> str:
    if not isinstance(value, Decimal):
        raise TypeError("Conversion values must be Decimal instances.")
    return format(value, "f")
