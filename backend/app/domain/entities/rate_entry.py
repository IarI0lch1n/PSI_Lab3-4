"""RateEntry domain entity representing a normalized exchange rate for a single currency."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from app.domain.entities.currency import (
    SUPPORTED_CRYPTO_CURRENCIES,
    SUPPORTED_FIAT_CURRENCIES,
    Currency,
    InvalidCurrencyError,
    UnsupportedCurrencyError,
)
from app.domain.enums.currency_type import CurrencyType
from app.domain.enums.freshness_state import FreshnessState


class RateEntryError(ValueError):
    """Raised when RateEntry validation fails."""


@dataclass(frozen=True)
class RateEntry:
    """Pure domain entity representing an individual currency exchange rate entry."""

    currency: str
    normalized_rate_to_mdl: Decimal
    provider_name: str
    provider_type: CurrencyType
    effective_at: datetime
    freshness_state: FreshnessState
    snapshot_id: UUID
    entry_id: UUID = field(default_factory=uuid4)
    nominal_unit: int | None = 1
    is_fallback: bool = False
    is_stale: bool = False

    def __post_init__(self) -> None:
        """Validate and normalize rate entry fields."""
        # 1. entry_id validation
        entry_id_val = self.entry_id
        if isinstance(entry_id_val, str):
            try:
                entry_id_val = UUID(entry_id_val)
            except ValueError as exc:
                raise RateEntryError(f"Invalid entry_id UUID string: {self.entry_id!r}") from exc
        elif not isinstance(entry_id_val, UUID):
            raise RateEntryError(
                f"entry_id must be a UUID or UUID string, got {type(entry_id_val).__name__}."
            )
        object.__setattr__(self, "entry_id", entry_id_val)

        # 2. snapshot_id validation
        snapshot_id_val = self.snapshot_id
        if isinstance(snapshot_id_val, str):
            try:
                snapshot_id_val = UUID(snapshot_id_val)
            except ValueError as exc:
                raise RateEntryError(f"Invalid snapshot_id UUID string: {self.snapshot_id!r}") from exc
        elif not isinstance(snapshot_id_val, UUID):
            raise RateEntryError(
                f"snapshot_id must be a UUID or UUID string, got {type(snapshot_id_val).__name__}."
            )
        object.__setattr__(self, "snapshot_id", snapshot_id_val)

        # 3. currency validation
        curr_val = self.currency
        if isinstance(curr_val, Currency):
            currency_code = curr_val.code
            expected_type = curr_val.type
        elif isinstance(curr_val, str):
            normalized_curr = curr_val.strip().upper()
            if not normalized_curr:
                raise InvalidCurrencyError("Currency code cannot be empty.")
            if normalized_curr in SUPPORTED_FIAT_CURRENCIES:
                currency_code = normalized_curr
                expected_type = CurrencyType.FIAT
            elif normalized_curr in SUPPORTED_CRYPTO_CURRENCIES:
                currency_code = normalized_curr
                expected_type = CurrencyType.CRYPTO
            else:
                raise UnsupportedCurrencyError(f"Currency '{normalized_curr}' is not supported.")
        else:
            raise InvalidCurrencyError(
                f"currency must be a Currency instance or valid string code, got {type(curr_val).__name__}."
            )
        object.__setattr__(self, "currency", currency_code)

        # 4. normalized_rate_to_mdl validation
        rate_val = self.normalized_rate_to_mdl
        if isinstance(rate_val, float):
            raise RateEntryError(
                "Binary floating-point is not permitted for normalized_rate_to_mdl; use Decimal or str."
            )
        if not isinstance(rate_val, Decimal):
            try:
                rate_val = Decimal(str(rate_val))
            except Exception as exc:
                raise RateEntryError(f"Invalid normalized_rate_to_mdl value: {rate_val!r}") from exc

        if rate_val.is_nan() or rate_val.is_infinite():
            raise RateEntryError("normalized_rate_to_mdl must be a finite Decimal.")
        if rate_val <= 0:
            raise RateEntryError(f"normalized_rate_to_mdl must be positive, got {rate_val}.")
        object.__setattr__(self, "normalized_rate_to_mdl", rate_val)

        # 5. nominal_unit validation
        nom_val = self.nominal_unit
        if nom_val is not None:
            if not isinstance(nom_val, int) or nom_val <= 0:
                raise RateEntryError(
                    f"nominal_unit must be a positive integer or None, got {nom_val!r}."
                )
        object.__setattr__(self, "nominal_unit", nom_val)

        # 6. provider_name validation
        if not isinstance(self.provider_name, str) or not self.provider_name.strip():
            raise RateEntryError("provider_name must be a non-empty string.")
        object.__setattr__(self, "provider_name", self.provider_name.strip())

        # 7. provider_type validation
        prov_type = self.provider_type
        if isinstance(prov_type, CurrencyType):
            normalized_prov_type = prov_type
        elif isinstance(prov_type, str):
            try:
                normalized_prov_type = CurrencyType(prov_type.strip().lower())
            except ValueError as exc:
                raise RateEntryError(f"Invalid provider_type: {prov_type!r}") from exc
        else:
            raise RateEntryError(
                f"provider_type must be a CurrencyType or valid string, got {type(prov_type).__name__}."
            )

        if normalized_prov_type != expected_type:
            raise RateEntryError(
                f"provider_type '{normalized_prov_type.value}' is inconsistent with currency '{currency_code}' ({expected_type.value})."
            )
        object.__setattr__(self, "provider_type", normalized_prov_type)

        # 8. effective_at validation (timezone-aware)
        eff_val = self.effective_at
        if not isinstance(eff_val, datetime):
            raise RateEntryError(f"effective_at must be a datetime, got {type(eff_val).__name__}.")
        if eff_val.tzinfo is None or eff_val.tzinfo.utcoffset(eff_val) is None:
            raise RateEntryError("effective_at must be a timezone-aware datetime.")
        object.__setattr__(self, "effective_at", eff_val)

        # 9. freshness_state validation
        fresh_val = self.freshness_state
        if isinstance(fresh_val, FreshnessState):
            normalized_fresh = fresh_val
        elif isinstance(fresh_val, str):
            try:
                normalized_fresh = FreshnessState(fresh_val.strip().lower())
            except ValueError as exc:
                raise RateEntryError(
                    f"Invalid freshness_state '{fresh_val}'; allowed values are: {[s.value for s in FreshnessState]}."
                ) from exc
        else:
            raise RateEntryError(
                f"freshness_state must be a FreshnessState or valid string, got {type(fresh_val).__name__}."
            )
        object.__setattr__(self, "freshness_state", normalized_fresh)

        # 10. is_fallback validation (strict boolean)
        if not isinstance(self.is_fallback, bool):
            raise RateEntryError(f"is_fallback must be a boolean, got {type(self.is_fallback).__name__}.")

        # 11. is_stale validation (strict boolean)
        if not isinstance(self.is_stale, bool):
            raise RateEntryError(f"is_stale must be a boolean, got {type(self.is_stale).__name__}.")
