"""Focused checks for the idempotent supported-currency seed."""

from uuid import UUID

from app.domain.entities.currency import (
    SUPPORTED_CRYPTO_CURRENCIES,
    SUPPORTED_FIAT_CURRENCIES,
)
from app.domain.enums.currency_type import CurrencyType
from app.infrastructure.database.models import CurrencyModel
from app.infrastructure.database.seed_currencies import (
    CURRENCY_SEED_DATA,
    seed_currencies,
)


class _ScalarResult:
    def __init__(self, values: list[str]) -> None:
        self._values = values

    def all(self) -> list[str]:
        return self._values


class _Result:
    def __init__(self, values: list[str]) -> None:
        self._values = values

    def scalars(self) -> _ScalarResult:
        return _ScalarResult(self._values)


class _FakeSession:
    def __init__(self) -> None:
        self.currencies: dict[str, CurrencyModel] = {}

    def execute(self, statement: object) -> _Result:
        del statement
        return _Result(list(self.currencies))

    def add_all(self, currencies: list[CurrencyModel]) -> None:
        self.currencies.update((currency.code, currency) for currency in currencies)


def test_seed_definition_matches_all_canonical_currencies() -> None:
    assert len(CURRENCY_SEED_DATA) == 18
    assert sum(kind is CurrencyType.FIAT for _, _, kind in CURRENCY_SEED_DATA) == 10
    assert sum(kind is CurrencyType.CRYPTO for _, _, kind in CURRENCY_SEED_DATA) == 8
    assert {
        code: name for code, name, kind in CURRENCY_SEED_DATA if kind is CurrencyType.FIAT
    } == dict(SUPPORTED_FIAT_CURRENCIES)
    assert {
        code: name for code, name, kind in CURRENCY_SEED_DATA if kind is CurrencyType.CRYPTO
    } == dict(SUPPORTED_CRYPTO_CURRENCIES)


def test_seed_operation_is_idempotent() -> None:
    session = _FakeSession()
    independent_session = _FakeSession()

    assert seed_currencies(session) == 18
    assert seed_currencies(independent_session) == 18
    first_ids = {code: row.id for code, row in session.currencies.items()}
    assert {
        code: row.id for code, row in independent_session.currencies.items()
    } == first_ids
    assert len(set(first_ids.values())) == 18
    assert all(isinstance(value, UUID) for value in first_ids.values())
    assert seed_currencies(session) == 0
    assert len(session.currencies) == 18
    assert {code: row.id for code, row in session.currencies.items()} == first_ids
