"""Tests for complete in-memory snapshot assembly."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.application.services.snapshot_service import (
    AssemblyReason,
    RateFreshnessMetadata,
    SnapshotAssemblyError,
    SnapshotService,
)
from app.domain.entities.currency import (
    SUPPORTED_CRYPTO_CURRENCIES,
    SUPPORTED_FIAT_CURRENCIES,
)
from app.domain.entities.rate_entry import RateEntry
from app.domain.entities.rate_snapshot import RateSnapshot
from app.domain.enums.currency_type import CurrencyType
from app.domain.enums.freshness_state import FreshnessState
from app.domain.interfaces.rate_provider import ProviderRate, RateProvider


_CAPTURED_AT = datetime(2026, 10, 28, 12, 0, tzinfo=UTC)
_CANONICAL_CODES = (
    *SUPPORTED_FIAT_CURRENCIES.keys(),
    *SUPPORTED_CRYPTO_CURRENCIES.keys(),
)


def _provider_rate(
    code: str,
    value: Decimal = Decimal("1.2345678901234567890123456789"),
    *,
    provider_name: str | None = None,
    effective_at: datetime = _CAPTURED_AT - timedelta(minutes=3),
    nominal_unit: int = 1,
) -> ProviderRate:
    provider_type = (
        CurrencyType.FIAT
        if code.strip().upper() in SUPPORTED_FIAT_CURRENCIES
        else CurrencyType.CRYPTO
    )
    return ProviderRate(
        currency=code,
        normalized_rate_to_mdl=value,
        nominal_unit=nominal_unit,
        provider_name=provider_name or f"{provider_type.value} source",
        provider_type=provider_type,
        effective_at=effective_at,
    )


def _current_rates() -> list[ProviderRate]:
    return [
        _provider_rate(code)
        for code in _CANONICAL_CODES
        if code != "MDL"
    ]


def _snapshot(
    rates: list[ProviderRate] | None = None,
    *,
    snapshot_id: UUID | None = None,
    mdl_rate: Decimal = Decimal("1"),
    mdl_nominal_unit: int = 1,
) -> RateSnapshot:
    rates = rates or _current_rates()
    snapshot_id = snapshot_id or uuid4()
    entries = [
        RateEntry(
            snapshot_id=snapshot_id,
            currency=rate.currency,
            normalized_rate_to_mdl=rate.normalized_rate_to_mdl,
            nominal_unit=rate.nominal_unit,
            provider_name=rate.provider_name,
            provider_type=rate.provider_type,
            effective_at=rate.effective_at,
            freshness_state=FreshnessState.LIVE,
        )
        for rate in rates
    ]
    entries.append(
        RateEntry(
            snapshot_id=snapshot_id,
            currency="MDL",
            normalized_rate_to_mdl=mdl_rate,
            nominal_unit=mdl_nominal_unit,
            provider_name="CurrencyHub Reference",
            provider_type=CurrencyType.FIAT,
            effective_at=_CAPTURED_AT,
            freshness_state=FreshnessState.LIVE,
        )
    )
    return RateSnapshot(snapshot_id, _CAPTURED_AT, entries)


class FakeProvider(RateProvider):
    def __init__(
        self,
        rates: list[ProviderRate] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.rates = rates or []
        self.error = error

    async def fetch_latest_rates(self):
        if self.error is not None:
            raise self.error
        return tuple(self.rates)

    async def fetch_historical_rates(self, currency_codes, start_at, end_at):
        raise NotImplementedError

    async def get_metadata(self):
        return {"provider_name": "fake"}


def _service(*providers: RateProvider, **kwargs) -> SnapshotService:
    return SnapshotService(
        providers,
        clock=lambda: _CAPTURED_AT,
        snapshot_id_factory=lambda: UUID("00000000-0000-0000-0000-000000000123"),
        **kwargs,
    )


@pytest.mark.asyncio
async def test_assembles_complete_snapshot_in_canonical_order_with_exact_decimal() -> None:
    service = _service(
        FakeProvider([rate for rate in _current_rates() if rate.currency != "BTC"]),
        FakeProvider([rate for rate in _current_rates() if rate.currency == "BTC"]),
    )

    snapshot = await service.assemble_snapshot()

    assert tuple(rate.currency for rate in snapshot.rates) == _CANONICAL_CODES
    assert snapshot.captured_at == _CAPTURED_AT
    assert snapshot.snapshot_id == UUID(
        "00000000-0000-0000-0000-000000000123"
    )
    assert snapshot.get_rate("MDL").normalized_rate_to_mdl == Decimal("1")
    assert snapshot.get_rate("BTC").normalized_rate_to_mdl == Decimal(
        "1.2345678901234567890123456789"
    )
    assert all(rate.snapshot_id == snapshot.snapshot_id for rate in snapshot.rates)
    assert all(rate.freshness_state is FreshnessState.LIVE for rate in snapshot.rates)
    assert not any(rate.is_fallback or rate.is_stale for rate in snapshot.rates)


@pytest.mark.asyncio
async def test_current_provider_rate_takes_priority_over_fallback_and_previous() -> None:
    current = _provider_rate("USD", Decimal("3"))
    fallback = _provider_rate("USD", Decimal("2"), provider_name="fallback source")
    previous = _snapshot(
        [
            rate
            for rate in _current_rates()
            if rate.currency != "USD"
        ]
        + [_provider_rate("USD", Decimal("4"), provider_name="old source")]
    )

    snapshot = await _service(
        FakeProvider([rate for rate in _current_rates() if rate.currency != "USD"] + [current])
    ).assemble_snapshot(
        explicit_fallback_rates=[fallback],
        previous_snapshot=previous,
    )

    usd = snapshot.get_rate("USD")
    assert usd.normalized_rate_to_mdl == Decimal("3")
    assert usd.provider_name == "fiat source"
    assert usd.freshness_state is FreshnessState.LIVE
    assert not usd.is_fallback


@pytest.mark.asyncio
async def test_explicit_fallback_is_marked_and_used_for_missing_provider_data() -> None:
    current = [rate for rate in _current_rates() if rate.currency != "JPY"]
    fallback = _provider_rate("JPY", Decimal("0.114754"), provider_name="BNM")

    snapshot = await _service(FakeProvider(current)).assemble_snapshot(
        explicit_fallback_rates=[fallback]
    )

    jpy = snapshot.get_rate("JPY")
    assert jpy.normalized_rate_to_mdl == Decimal("0.114754")
    assert jpy.freshness_state is FreshnessState.FALLBACK
    assert jpy.is_fallback
    assert not jpy.is_stale


@pytest.mark.asyncio
async def test_previous_snapshot_reuse_is_cached_without_resetting_provenance() -> None:
    previous_rate = _provider_rate(
        "DOGE",
        Decimal("0.000123456789"),
        provider_name="older crypto source",
        effective_at=_CAPTURED_AT - timedelta(days=2),
    )
    previous = _snapshot(
        [
            rate
            for rate in _current_rates()
            if rate.currency != "DOGE"
        ]
        + [previous_rate]
    )
    current = [rate for rate in _current_rates() if rate.currency != "DOGE"]

    snapshot = await _service(FakeProvider(current)).assemble_snapshot(
        previous_snapshot=previous
    )

    reused = snapshot.get_rate("DOGE")
    assert reused.normalized_rate_to_mdl == previous_rate.normalized_rate_to_mdl
    assert reused.provider_name == "older crypto source"
    assert reused.effective_at == previous_rate.effective_at
    assert reused.snapshot_id == snapshot.snapshot_id
    assert reused.freshness_state is FreshnessState.CACHED
    assert not reused.is_fallback


@pytest.mark.asyncio
async def test_provider_failure_does_not_discard_complete_results_from_another_source() -> None:
    snapshot = await _service(
        FakeProvider(error=RuntimeError("provider unavailable")),
        FakeProvider(_current_rates()),
    ).assemble_snapshot()

    assert len(snapshot.rates) == 18


@pytest.mark.asyncio
async def test_missing_currency_without_permitted_source_fails_with_provider_cause() -> None:
    provider_error = RuntimeError("network unavailable")
    service = _service(
        FakeProvider([rate for rate in _current_rates() if rate.currency != "XRP"]),
        FakeProvider(error=provider_error),
    )

    with pytest.raises(SnapshotAssemblyError, match="XRP") as exc_info:
        await service.assemble_snapshot()

    assert exc_info.value.__cause__ is provider_error


@pytest.mark.asyncio
async def test_incomplete_previous_snapshot_is_not_used_to_fill_missing_data() -> None:
    previous = _snapshot(_current_rates()[:-1])
    current = [rate for rate in _current_rates() if rate.currency != "XRP"]

    with pytest.raises(SnapshotAssemblyError, match="previous snapshot is unusable"):
        await _service(FakeProvider(current)).assemble_snapshot(
            previous_snapshot=previous
        )


@pytest.mark.parametrize(
    ("mdl_rate", "mdl_nominal_unit"),
    [
        (Decimal("2"), 1),
        (Decimal("1"), 10),
    ],
)
@pytest.mark.asyncio
async def test_invalid_previous_mdl_reference_is_not_used_to_fill_missing_data(
    mdl_rate: Decimal,
    mdl_nominal_unit: int,
) -> None:
    previous = _snapshot(
        mdl_rate=mdl_rate,
        mdl_nominal_unit=mdl_nominal_unit,
    )
    current = [rate for rate in _current_rates() if rate.currency != "XRP"]

    with pytest.raises(
        SnapshotAssemblyError,
        match="previous snapshot is unusable.*MDL reference",
    ):
        await _service(FakeProvider(current)).assemble_snapshot(
            previous_snapshot=previous
        )


@pytest.mark.asyncio
async def test_freshness_policy_is_injectable_and_receives_assembly_reason() -> None:
    observed_reasons: set[AssemblyReason] = set()

    def policy(rate, captured_at, reason):
        del rate, captured_at
        observed_reasons.add(reason)
        if reason is AssemblyReason.PROVIDER_CURRENT:
            return RateFreshnessMetadata(FreshnessState.LIVE, False, True)
        if reason is AssemblyReason.EXPLICIT_FALLBACK:
            return RateFreshnessMetadata(FreshnessState.FALLBACK, True, True)
        if reason is AssemblyReason.MDL_REFERENCE:
            return RateFreshnessMetadata(FreshnessState.LIVE, False, False)
        return RateFreshnessMetadata(FreshnessState.CACHED, False, True)

    rates = [rate for rate in _current_rates() if rate.currency != "USD"]
    snapshot = await _service(
        FakeProvider(rates),
        freshness_policy=policy,
    ).assemble_snapshot(explicit_fallback_rates=[_provider_rate("USD")])

    assert observed_reasons == {
        AssemblyReason.PROVIDER_CURRENT,
        AssemblyReason.EXPLICIT_FALLBACK,
        AssemblyReason.MDL_REFERENCE,
    }
    assert snapshot.get_rate("USD").is_stale
    assert snapshot.get_rate("USD").is_fallback


@pytest.mark.parametrize(
    ("mutations", "message"),
    [
        ({"currency": "   "}, "empty currency"),
        ({"currency": "ZZZ"}, "unsupported currency"),
        ({"currency": "USD", "normalized_rate_to_mdl": 1.2}, "Decimal"),
        (
            {"currency": "USD", "normalized_rate_to_mdl": Decimal("0")},
            "positive finite Decimal",
        ),
        (
            {"currency": "USD", "effective_at": datetime(2026, 10, 28)},
            "timezone-aware effective_at",
        ),
        ({"currency": "USD", "nominal_unit": 0}, "nominal_unit"),
    ],
)
@pytest.mark.asyncio
async def test_invalid_provider_data_is_rejected(mutations, message) -> None:
    rates = _current_rates()
    target_index = next(
        index for index, rate in enumerate(rates) if rate.currency == "USD"
    )
    rate = rates[target_index]
    rates[target_index] = ProviderRate(
        currency=mutations.get("currency", rate.currency),
        normalized_rate_to_mdl=mutations.get(
            "normalized_rate_to_mdl", rate.normalized_rate_to_mdl
        ),
        nominal_unit=mutations.get("nominal_unit", rate.nominal_unit),
        provider_name=rate.provider_name,
        provider_type=rate.provider_type,
        effective_at=mutations.get("effective_at", rate.effective_at),
    )

    with pytest.raises(SnapshotAssemblyError, match=message):
        await _service(FakeProvider(rates)).assemble_snapshot()


@pytest.mark.asyncio
async def test_duplicate_provider_currency_is_rejected_after_normalization() -> None:
    rates = _current_rates()
    duplicate_usd = _provider_rate("usd")

    with pytest.raises(SnapshotAssemblyError, match="duplicate currency USD"):
        await _service(FakeProvider(rates + [duplicate_usd])).assemble_snapshot()


@pytest.mark.asyncio
async def test_provider_cannot_supply_internal_mdl_reference() -> None:
    rates = _current_rates() + [_provider_rate("MDL")]

    with pytest.raises(SnapshotAssemblyError, match="internal MDL reference"):
        await _service(FakeProvider(rates)).assemble_snapshot()


@pytest.mark.asyncio
async def test_explicit_fallback_input_is_validated_and_duplicates_are_rejected() -> None:
    rates = _current_rates()
    fallback = _provider_rate("USD")

    with pytest.raises(SnapshotAssemblyError, match="duplicate currency USD"):
        await _service(FakeProvider(rates)).assemble_snapshot(
            explicit_fallback_rates=[fallback, fallback]
        )
