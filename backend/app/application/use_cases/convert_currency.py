"""Use case for converting an amount using one usable rate snapshot."""

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from app.domain.entities.currency import (
    SUPPORTED_CRYPTO_CURRENCIES,
    SUPPORTED_FIAT_CURRENCIES,
)
from app.domain.entities.rate_entry import RateEntry
from app.domain.interfaces.unit_of_work import UnitOfWork
from app.domain.value_objects.money import InvalidMoneyError, Money


class ConversionError(Exception):
    """Base class for controlled conversion use-case errors."""


class InvalidConversionInputError(ConversionError):
    """Raised when an amount or currency input is invalid."""


class ConversionSnapshotUnavailableError(ConversionError):
    """Raised when no usable snapshot exists for conversion."""

    def __init__(self) -> None:
        super().__init__("No usable rate snapshot is available for conversion.")


class ConversionRateUnavailableError(ConversionError):
    """Raised when a required currency rate is absent from the selected snapshot."""

    def __init__(self, currency: str) -> None:
        self.currency = currency
        super().__init__(f"No usable rate is available for {currency}.")


@dataclass(frozen=True)
class ConversionResult:
    """Conversion values and the exact rate entries used to produce them."""

    source_amount: Decimal
    converted_amount: Decimal
    source_currency: str
    target_currency: str
    rate_value: Decimal
    snapshot_id: UUID
    source_rate: RateEntry
    target_rate: RateEntry


class ConvertCurrency:
    """Convert between supported currencies using one repository-selected snapshot."""

    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    def execute(
        self,
        amount: Decimal | str | int | None,
        source_currency: object,
        target_currency: object,
    ) -> ConversionResult:
        """Validate inputs and calculate a Decimal conversion from one snapshot."""
        source_code = self._normalize_currency(source_currency, "Source")
        target_code = self._normalize_currency(target_currency, "Target")
        source_amount = self._validated_amount(amount)

        with self._unit_of_work as uow:
            snapshot = uow.rate_repository.get_latest_usable_snapshot()
            if snapshot is None:
                raise ConversionSnapshotUnavailableError

            source_rate = snapshot.get_rate(source_code)
            if source_rate is None:
                raise ConversionRateUnavailableError(source_code)

            target_rate = (
                source_rate
                if source_code == target_code
                else snapshot.get_rate(target_code)
            )
            if target_rate is None:
                raise ConversionRateUnavailableError(target_code)

            if source_code == target_code:
                rate_value = Decimal(1)
                converted_amount = source_amount
            else:
                rate_value = (
                    source_rate.normalized_rate_to_mdl
                    / target_rate.normalized_rate_to_mdl
                )
                converted_amount = source_amount * rate_value

            return ConversionResult(
                source_amount=source_amount,
                converted_amount=converted_amount,
                source_currency=source_code,
                target_currency=target_code,
                rate_value=rate_value,
                snapshot_id=snapshot.snapshot_id,
                source_rate=source_rate,
                target_rate=target_rate,
            )

    @staticmethod
    def _validated_amount(amount: object) -> Decimal:
        if (
            amount is None
            or isinstance(amount, (bool, float))
            or not isinstance(amount, (Decimal, str, int))
        ):
            raise InvalidConversionInputError(
                "Amount must be a finite number greater than zero."
            )
        try:
            return Money(amount).amount
        except InvalidMoneyError as exc:
            raise InvalidConversionInputError(
                "Amount must be a finite number greater than zero."
            ) from exc

    @staticmethod
    def _normalize_currency(currency: object, label: str) -> str:
        message = f"{label} currency must be a supported currency code."
        if not isinstance(currency, str):
            raise InvalidConversionInputError(message)

        code = currency.strip().upper()
        if not code or (
            code not in SUPPORTED_FIAT_CURRENCIES
            and code not in SUPPORTED_CRYPTO_CURRENCIES
        ):
            raise InvalidConversionInputError(message)
        return code
