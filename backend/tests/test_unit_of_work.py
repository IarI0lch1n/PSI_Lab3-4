"""Tests for SQLAlchemy Unit of Work transaction boundaries."""

from decimal import Decimal
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.domain.entities.rate_entry import RateEntry
from app.domain.entities.rate_snapshot import RateSnapshot
from app.domain.enums.currency_type import CurrencyType
from app.domain.enums.freshness_state import FreshnessState
from app.infrastructure.database.models import RateEntryModel, RateSnapshotModel
from app.infrastructure.database.unit_of_work import SqlAlchemyUnitOfWork


class _FakeSession:
    def __init__(self) -> None:
        self.added: list[object] = []
        self.added_all: list[object] = []
        self.commit_calls = 0
        self.rollback_calls = 0
        self.close_calls = 0
        self.flush_calls = 0

    def get(self, model: type[object], identity: object) -> None:
        del model, identity
        return None

    def add(self, instance: object) -> None:
        self.added.append(instance)

    def add_all(self, instances: list[object]) -> None:
        self.added_all.extend(instances)

    def flush(self) -> None:
        self.flush_calls += 1

    def commit(self) -> None:
        self.commit_calls += 1

    def rollback(self) -> None:
        self.rollback_calls += 1

    def close(self) -> None:
        self.close_calls += 1


class _SessionFactory:
    def __init__(self, session: _FakeSession) -> None:
        self.session = session

    def __call__(self) -> _FakeSession:
        return self.session


def _snapshot() -> RateSnapshot:
    snapshot_id = uuid4()
    captured_at = datetime(2026, 10, 28, 8, tzinfo=UTC)
    return RateSnapshot(
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
            ),
            RateEntry(
                snapshot_id=snapshot_id,
                currency="BTC",
                normalized_rate_to_mdl=Decimal("900000.125"),
                provider_name="CoinGecko",
                provider_type=CurrencyType.CRYPTO,
                effective_at=captured_at,
                freshness_state=FreshnessState.LIVE,
            ),
        ],
    )


def test_repositories_share_one_session_and_each_commit_is_forwarded() -> None:
    session = _FakeSession()
    uow = SqlAlchemyUnitOfWork(session_factory=_SessionFactory(session))

    with uow:
        assert uow.currency_repository._session is session
        assert uow.rate_repository._session is session
        uow.commit()
        uow.commit()

    assert session.commit_calls == 2
    assert session.rollback_calls == 1
    assert session.close_calls == 1


def test_uncommitted_context_rolls_back_and_closes() -> None:
    session = _FakeSession()

    with SqlAlchemyUnitOfWork(session_factory=_SessionFactory(session)):
        pass

    assert session.commit_calls == 0
    assert session.rollback_calls == 1
    assert session.close_calls == 1


def test_explicit_rollback_and_exception_rollback() -> None:
    manual_session = _FakeSession()
    with SqlAlchemyUnitOfWork(session_factory=_SessionFactory(manual_session)) as uow:
        uow.rollback()
        uow.rollback()
    assert manual_session.rollback_calls == 3
    assert manual_session.close_calls == 1

    exception_session = _FakeSession()
    with pytest.raises(RuntimeError, match="failure"):
        with SqlAlchemyUnitOfWork(
            session_factory=_SessionFactory(exception_session)
        ):
            raise RuntimeError("failure")
    assert exception_session.rollback_calls == 1
    assert exception_session.close_calls == 1


def test_repository_save_defers_commit_to_unit_of_work_and_exit_is_safe() -> None:
    session = _FakeSession()
    with SqlAlchemyUnitOfWork(session_factory=_SessionFactory(session)) as uow:
        uow.rate_repository.save_complete_snapshot(_snapshot())
        assert len(session.added) == 1
        assert len(session.added_all) == 2
        assert isinstance(session.added[0], RateSnapshotModel)
        assert all(isinstance(entry, RateEntryModel) for entry in session.added_all)
        assert session.flush_calls == 1
        assert session.commit_calls == 0
        uow.commit()

    assert session.commit_calls == 1
    assert session.rollback_calls == 1
    assert session.close_calls == 1


def test_context_exit_after_commit_discards_later_uncommitted_work() -> None:
    session = _FakeSession()

    with SqlAlchemyUnitOfWork(session_factory=_SessionFactory(session)) as uow:
        uow.commit()
        uow.rate_repository.save_complete_snapshot(_snapshot())

    assert session.commit_calls == 1
    assert session.rollback_calls == 1
    assert session.close_calls == 1
