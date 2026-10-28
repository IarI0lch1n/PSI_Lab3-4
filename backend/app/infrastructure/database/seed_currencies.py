"""Idempotent seed operation for the supported currency catalog."""

from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.currency import (
    SUPPORTED_CRYPTO_CURRENCIES,
    SUPPORTED_FIAT_CURRENCIES,
)
from app.domain.enums.currency_type import CurrencyType
from app.infrastructure.database.models import CurrencyModel


CURRENCY_SEED_DATA: tuple[tuple[str, str, CurrencyType], ...] = tuple(
    (code, name, CurrencyType.FIAT)
    for code, name in SUPPORTED_FIAT_CURRENCIES.items()
) + tuple(
    (code, name, CurrencyType.CRYPTO)
    for code, name in SUPPORTED_CRYPTO_CURRENCIES.items()
)


def seed_currencies(session: Session) -> int:
    """Insert missing supported currencies and return the number inserted.

    Transaction commit and rollback remain the caller's responsibility.
    """
    existing_codes = set(session.execute(select(CurrencyModel.code)).scalars().all())
    missing_currencies = [
        CurrencyModel(
            id=uuid5(NAMESPACE_URL, f"currencyhub:currency:{code}"),
            code=code,
            name=name,
            type=currency_type,
            is_supported=True,
        )
        for code, name, currency_type in CURRENCY_SEED_DATA
        if code not in existing_codes
    ]
    if missing_currencies:
        session.add_all(missing_currencies)
    return len(missing_currencies)
