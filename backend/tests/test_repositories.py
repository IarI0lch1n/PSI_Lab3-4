"""Focused tests for SQLAlchemy-backed currency and rate repositories."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy.dialects import mssql

from app.domain.entities.rate_entry import RateEntry
from app.domain.entities.rate_snapshot import RateSnapshot
from app.domain.enums.currency_type import CurrencyType
from app.domain.enums.freshness_state import FreshnessState
from app.infrastructure.database.models import (
    CurrencyModel,
    RateEntryModel,
    RateSnapshotModel,
)
from app.infrastructure.repositories.currency_repository import (
    SqlAlchemyCurrencyRepository,
)
from app.infrastructure.repositories.rate_repository import (
    RateStalenessContext,
    SqlAlchemyRateRepository,
)


class _ScalarRows:
    def __init__(self, rows: list[object]) -> None:
        self._rows = rows

    def all(self) -> list[object]:
        return self._rows

    def first(self) -> object | None:
        return self._rows[0] if self._rows else None


class _Result:
    def __init__(self, rows: list[object]) -> None:
        self._rows = rows

    def scalars(self) -> _ScalarRows:
        return _ScalarRows(self._rows)

    def all(self) -> list[object]:
        return self._rows


class _Session:
    def __init__(self, results: list[_Result] | None = None) -> None:
        self.results = list(results or [])
        self.statements: list[object] = []
        self.added: list[object] = []
        self.added_all: list[object] = []
        self.flush_calls = 0
        self.commit_calls = 0
        self.existing: object | None = None

    def execute(self, statement: object) -> _Result:
        self.statements.append(statement)
        return self.results.pop(0)

    def get(self, model: type[object], identity: object) -> object | None:
        del model, identity
        return self.existing

    def add(self, instance: object) -> None:
        self.added.append(instance)

    def add_all(self, instances: list[object]) -> None:
        self.added_all.extend(instances)

    def flush(self) -> None:
        self.flush_calls += 1


def _snapshot_models(
    snapshot_id: UUID | None = None,
    entry_id: UUID | None = None,
    captured_at: datetime | None = None,
    effective_at: datetime | None = None,
    currency_code: str = "USD",
) -> tuple[RateSnapshotModel, RateEntryModel]:
    snapshot_id = snapshot_id or uuid4()
    captured_at = captured_at or datetime(2026, 10, 28, 8, tzinfo=UTC)
    effective_at = effective_at or datetime(2026, 10, 28, 7, tzinfo=UTC)
    snapshot = RateSnapshotModel(id=snapshot_id, captured_at=captured_at)
    entry = RateEntryModel(
        id=entry_id or uuid4(),
        snapshot_id=snapshot_id,
        currency_code=currency_code,
        normalized_rate_to_mdl=Decimal("17.123456789012345678"),
        nominal_unit=10,
        provider_name="BNM",
        provider_type=CurrencyType.FIAT,
        effective_at=effective_at,
        freshness_state=FreshnessState.FALLBACK,
        is_fallback=True,
    )
    return snapshot, entry


def test_currency_repository_maps_supported_currencies_and_normalizes_lookup() -> None:
    rows = [
        CurrencyModel(
            code="EUR",
            name="Euro",
            type=CurrencyType.FIAT,
            is_supported=True,
        ),
        CurrencyModel(
            code="USD",
            name="US Dollar",
            type=CurrencyType.FIAT,
            is_supported=True,
        ),
    ]
    session = _Session([_Result(rows), _Result([rows[1]])])
    repository = SqlAlchemyCurrencyRepository(session)

    currencies = repository.get_supported_currencies()
    found = repository.get_currency_by_code(" usd ")

    assert [currency.code for currency in currencies] == ["EUR", "USD"]
    assert all(not isinstance(currency, CurrencyModel) for currency in currencies)
    assert found is not None and found.code == "USD"
    assert not isinstance(found, CurrencyModel)
    assert "ORDER BY currencies.code ASC" in str(session.statements[0])


def test_currency_repository_returns_none_for_missing_code() -> None:
    repository = SqlAlchemyCurrencyRepository(_Session([_Result([])]))

    assert repository.get_currency_by_code("missing") is None


def test_currency_supported_predicates_compile_for_mssql() -> None:
    currencies = CurrencyModel(
        code="USD",
        name="US Dollar",
        type=CurrencyType.FIAT,
        is_supported=True,
    )
    session = _Session(
        [_Result([currencies]), _Result([currencies])]
    )
    repository = SqlAlchemyCurrencyRepository(session)

    repository.get_supported_currencies()
    repository.get_currency_by_code("USD")

    compiled_statements = [
        str(statement.compile(dialect=mssql.dialect()))
        for statement in session.statements
    ]
    assert all("currencies.is_supported = 1" in sql for sql in compiled_statements)
    assert all("IS 1" not in sql for sql in compiled_statements)


def test_rate_mapping_preserves_ids_decimal_metadata_and_uses_resolver() -> None:
    snapshot_model, entry_model = _snapshot_models()
    seen: list[RateStalenessContext] = []

    def resolve_stale(context: RateStalenessContext) -> bool:
        seen.append(context)
        return context.provider_type is CurrencyType.FIAT

    session = _Session(
        [_Result([snapshot_model]), _Result([entry_model])]
    )
    snapshot = SqlAlchemyRateRepository(
        session, staleness_resolver=resolve_stale
    ).get_snapshot_by_id(snapshot_model.id)

    assert snapshot is not None
    rate = snapshot.rates[0]
    assert snapshot.snapshot_id == snapshot_model.id
    assert snapshot.captured_at == snapshot_model.captured_at
    assert rate.entry_id == entry_model.id
    assert rate.snapshot_id == snapshot_model.id
    assert rate.currency == "USD"
    assert rate.normalized_rate_to_mdl == Decimal("17.123456789012345678")
    assert rate.nominal_unit == 10
    assert rate.provider_name == "BNM"
    assert rate.provider_type is CurrencyType.FIAT
    assert rate.effective_at == entry_model.effective_at
    assert rate.freshness_state is FreshnessState.FALLBACK
    assert rate.is_fallback is True
    assert rate.is_stale is True
    assert seen[0].captured_at == snapshot_model.captured_at
    assert "is_stale" not in RateEntryModel.__table__.columns


def test_rate_staleness_default_is_conservative_and_not_persisted() -> None:
    snapshot_model, entry_model = _snapshot_models()
    repository = SqlAlchemyRateRepository(
        _Session([_Result([snapshot_model]), _Result([entry_model])])
    )

    hydrated = repository.get_snapshot_by_id(snapshot_model.id)

    assert hydrated is not None
    assert hydrated.rates[0].is_stale is False
    assert "is_stale" not in RateEntryModel.__table__.columns


def test_save_snapshot_adds_every_model_and_flushes_without_commit() -> None:
    snapshot_id = uuid4()
    captured_at = datetime(2026, 10, 28, 8, tzinfo=UTC)
    rates = (
        RateEntry(
            snapshot_id=snapshot_id,
            currency="USD",
            normalized_rate_to_mdl=Decimal("17.25"),
            nominal_unit=1,
            provider_name="BNM",
            provider_type=CurrencyType.FIAT,
            effective_at=captured_at - timedelta(minutes=1),
            freshness_state=FreshnessState.LIVE,
        ),
        RateEntry(
            snapshot_id=snapshot_id,
            currency="BTC",
            normalized_rate_to_mdl=Decimal("900000.125"),
            nominal_unit=1,
            provider_name="CoinGecko",
            provider_type=CurrencyType.CRYPTO,
            effective_at=captured_at,
            freshness_state=FreshnessState.LIVE,
        ),
    )
    domain_snapshot = RateSnapshot(snapshot_id, captured_at, rates)
    session = _Session()

    SqlAlchemyRateRepository(session).save_complete_snapshot(domain_snapshot)

    assert len(session.added) == 1
    assert isinstance(session.added[0], RateSnapshotModel)
    assert session.added[0].id == snapshot_id
    assert len(session.added_all) == 2
    assert all(isinstance(row, RateEntryModel) for row in session.added_all)
    assert {row.id for row in session.added_all} == {
        rate.entry_id for rate in domain_snapshot.rates
    }
    assert {row.normalized_rate_to_mdl for row in session.added_all} == {
        rate.normalized_rate_to_mdl for rate in domain_snapshot.rates
    }
    assert session.flush_calls == 1
    assert session.commit_calls == 0


def test_save_snapshot_rejects_duplicate_snapshot_id() -> None:
    session = _Session()
    session.existing = object()
    repository = SqlAlchemyRateRepository(session)
    snapshot_id = uuid4()

    captured_at = datetime(2026, 10, 28, 8, tzinfo=UTC)
    snapshot = RateSnapshot(
        snapshot_id,
        captured_at,
        [
            RateEntry(
                snapshot_id=snapshot_id,
                currency="USD",
                normalized_rate_to_mdl=Decimal("17.25"),
                provider_name="BNM",
                provider_type=CurrencyType.FIAT,
                effective_at=captured_at,
                freshness_state=FreshnessState.LIVE,
            )
        ],
    )

    with pytest.raises(ValueError, match="already exists"):
        repository.save_complete_snapshot(snapshot)
    assert session.added == []
    assert session.added_all == []


def test_snapshot_lookup_returns_none_when_missing() -> None:
    repository = SqlAlchemyRateRepository(_Session([_Result([])]))

    assert repository.get_snapshot_by_id(uuid4()) is None


def test_latest_snapshot_query_uses_deterministic_newest_ordering() -> None:
    snapshot_model, entry_model = _snapshot_models()
    session = _Session(
        [_Result([snapshot_model]), _Result([entry_model])]
    )

    snapshot = SqlAlchemyRateRepository(session).get_latest_usable_snapshot()

    assert snapshot is not None
    assert snapshot.snapshot_id == snapshot_model.id
    latest_statement = str(session.statements[0])
    assert "ORDER BY rate_snapshots.captured_at DESC, rate_snapshots.id DESC" in latest_statement
    assert "LIMIT" in latest_statement


def test_historical_query_orders_snapshots_and_filters_normalized_currencies() -> None:
    snapshot_early, early_entry = _snapshot_models(
        captured_at=datetime(2026, 10, 27, 8, tzinfo=UTC),
        currency_code="USD",
    )
    snapshot_late, late_entry = _snapshot_models(
        captured_at=datetime(2026, 10, 28, 8, tzinfo=UTC),
        currency_code="USD",
    )
    session = _Session(
        [
            _Result(
                [
                    (snapshot_early, early_entry),
                    (snapshot_late, late_entry),
                ]
            )
        ]
    )
    start = datetime(2026, 10, 27, tzinfo=UTC)
    end = datetime(2026, 10, 28, 23, tzinfo=UTC)

    snapshots = SqlAlchemyRateRepository(session).get_historical_snapshots(
        start, end, [" usd "]
    )

    assert [snapshot.captured_at for snapshot in snapshots] == [
        snapshot_early.captured_at,
        snapshot_late.captured_at,
    ]
    assert all([rate.currency for rate in snapshot.rates] == ["USD"] for snapshot in snapshots)
    query = str(session.statements[0])
    assert "ORDER BY rate_snapshots.captured_at ASC" in query
    assert "rate_entries.currency_code IN" in query


def test_historical_query_empty_currency_filter_returns_no_snapshots() -> None:
    session = _Session()
    results = SqlAlchemyRateRepository(session).get_historical_snapshots(
        datetime(2026, 10, 1, tzinfo=UTC),
        datetime(2026, 10, 28, tzinfo=UTC),
        [],
    )

    assert results == ()
    assert session.statements == []
    assert "is_stale" not in RateEntryModel.__table__.columns
    assert "pair" not in RateSnapshotModel.__table__.columns
