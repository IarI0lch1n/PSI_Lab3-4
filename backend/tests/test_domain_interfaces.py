"""Focused checks for domain interface contracts."""

import inspect
from collections.abc import Sequence
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from decimal import Decimal
from typing import get_type_hints

import pytest

from app.domain.interfaces import (
    CurrencyRepository,
    ProviderRate,
    RateProvider,
    RateRepository,
    UnitOfWork,
)
from app.domain.enums.currency_type import CurrencyType


@pytest.mark.parametrize(
    "interface",
    [CurrencyRepository, RateProvider, RateRepository, UnitOfWork],
)
def test_domain_interfaces_are_abstract(interface: type[object]) -> None:
    assert inspect.isabstract(interface)
    with pytest.raises(TypeError):
        interface()


def test_rate_provider_network_contract_is_async() -> None:
    assert inspect.iscoroutinefunction(RateProvider.fetch_latest_rates)
    assert inspect.iscoroutinefunction(RateProvider.fetch_historical_rates)
    assert inspect.iscoroutinefunction(RateProvider.get_metadata)


def test_provider_rate_is_immutable_and_has_no_snapshot_assembly_fields() -> None:
    rate = ProviderRate(
        currency="USD",
        normalized_rate_to_mdl=Decimal("17.5"),
        nominal_unit=1,
        provider_name="Example",
        provider_type=CurrencyType.FIAT,
        effective_at=datetime(2026, 10, 23, tzinfo=UTC),
    )

    with pytest.raises(FrozenInstanceError):
        setattr(rate, "currency", "EUR")

    assert {
        "snapshot_id",
        "entry_id",
        "freshness_state",
        "is_fallback",
        "is_stale",
    }.isdisjoint(ProviderRate.__dataclass_fields__)


def test_provider_fetch_methods_return_provider_rates() -> None:
    assert get_type_hints(RateProvider.fetch_latest_rates)["return"] == Sequence[ProviderRate]
    assert (
        get_type_hints(RateProvider.fetch_historical_rates)["return"] == Sequence[ProviderRate]
    )
