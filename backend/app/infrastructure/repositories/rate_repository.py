"""SQLAlchemy-backed repository for normalized rate snapshots."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.rate_entry import RateEntry
from app.domain.entities.rate_snapshot import RateSnapshot
from app.domain.enums.currency_type import CurrencyType
from app.domain.enums.freshness_state import FreshnessState
from app.domain.interfaces.rate_repository import RateRepository
from app.infrastructure.database.models import RateEntryModel, RateSnapshotModel


@dataclass(frozen=True)
class RateStalenessContext:
    """Persistence metadata provided to an injectable stale-state resolver."""

    snapshot_id: UUID
    captured_at: datetime
    currency_code: str
    provider_name: str
    provider_type: CurrencyType
    effective_at: datetime
    freshness_state: FreshnessState
    is_fallback: bool


StalenessResolver = Callable[[RateStalenessContext], bool]


def _persistence_only_staleness_default(context: RateStalenessContext) -> bool:
    """Do not infer stale status from persistence metadata without freshness policy."""
    del context
    return False


class SqlAlchemyRateRepository(RateRepository):
    """Persist and hydrate rate snapshots using the caller-owned session."""

    def __init__(
        self,
        session: Session,
        staleness_resolver: StalenessResolver | None = None,
    ) -> None:
        self._session = session
        self._staleness_resolver = (
            staleness_resolver or _persistence_only_staleness_default
        )

    def get_latest_usable_snapshot(self) -> RateSnapshot | None:
        statement = (
            select(RateSnapshotModel)
            .join(RateSnapshotModel.entries)
            .order_by(
                RateSnapshotModel.captured_at.desc(),
                RateSnapshotModel.id.desc(),
            )
            .limit(1)
        )
        snapshot_model = self._session.execute(statement).scalars().first()
        if snapshot_model is None:
            return None
        return self._load_snapshot(snapshot_model)

    def get_snapshot_by_id(self, snapshot_id: UUID) -> RateSnapshot | None:
        statement = select(RateSnapshotModel).where(
            RateSnapshotModel.id == snapshot_id
        )
        snapshot_model = self._session.execute(statement).scalars().first()
        if snapshot_model is None:
            return None
        return self._load_snapshot(snapshot_model)

    def save_complete_snapshot(self, snapshot: RateSnapshot) -> None:
        if self._session.get(RateSnapshotModel, snapshot.snapshot_id) is not None:
            raise ValueError(f"Snapshot '{snapshot.snapshot_id}' already exists.")

        snapshot_model = RateSnapshotModel(
            id=snapshot.snapshot_id,
            captured_at=snapshot.captured_at,
        )
        entry_models = [
            RateEntryModel(
                id=rate.entry_id,
                snapshot_id=snapshot.snapshot_id,
                currency_code=rate.currency,
                normalized_rate_to_mdl=rate.normalized_rate_to_mdl,
                nominal_unit=rate.nominal_unit,
                provider_name=rate.provider_name,
                provider_type=rate.provider_type,
                effective_at=rate.effective_at,
                freshness_state=rate.freshness_state,
                is_fallback=rate.is_fallback,
            )
            for rate in snapshot.rates
        ]
        self._session.add(snapshot_model)
        self._session.add_all(entry_models)
        self._session.flush()

    def get_historical_snapshots(
        self,
        start_at: datetime,
        end_at: datetime,
        currency_codes: Sequence[str] | None = None,
    ) -> Sequence[RateSnapshot]:
        if start_at.tzinfo is None or start_at.utcoffset() is None:
            raise ValueError("Historical start_at must be timezone-aware.")
        if end_at.tzinfo is None or end_at.utcoffset() is None:
            raise ValueError("Historical end_at must be timezone-aware.")
        if start_at > end_at:
            raise ValueError("Historical start_at must not follow end_at.")
        normalized_codes = (
            {code.strip().upper() for code in currency_codes}
            if currency_codes is not None
            else None
        )
        if normalized_codes == set():
            return ()

        statement = (
            select(RateSnapshotModel, RateEntryModel)
            .join(RateEntryModel, RateEntryModel.snapshot_id == RateSnapshotModel.id)
            .where(
                RateSnapshotModel.captured_at >= start_at,
                RateSnapshotModel.captured_at <= end_at,
            )
            .order_by(
                RateSnapshotModel.captured_at.asc(),
                RateSnapshotModel.id.asc(),
                RateEntryModel.currency_code.asc(),
            )
        )
        if normalized_codes is not None:
            statement = statement.where(
                RateEntryModel.currency_code.in_(normalized_codes)
            )

        snapshots: dict[UUID, tuple[RateSnapshotModel, list[RateEntryModel]]] = {}
        for snapshot_model, entry_model in self._session.execute(statement).all():
            group = snapshots.setdefault(snapshot_model.id, (snapshot_model, []))
            group[1].append(entry_model)

        return tuple(
            self._to_domain(snapshot_model, entries)
            for snapshot_model, entries in snapshots.values()
        )

    def _load_snapshot(self, snapshot_model: RateSnapshotModel) -> RateSnapshot | None:
        statement = (
            select(RateEntryModel)
            .where(RateEntryModel.snapshot_id == snapshot_model.id)
            .order_by(RateEntryModel.currency_code.asc())
        )
        entries = self._session.execute(statement).scalars().all()
        if not entries:
            return None
        return self._to_domain(snapshot_model, entries)

    def _to_domain(
        self,
        snapshot_model: RateSnapshotModel,
        entry_models: Sequence[RateEntryModel],
    ) -> RateSnapshot:
        rates = tuple(
            RateEntry(
                snapshot_id=snapshot_model.id,
                entry_id=entry.id,
                currency=entry.currency_code,
                normalized_rate_to_mdl=entry.normalized_rate_to_mdl,
                nominal_unit=entry.nominal_unit,
                provider_name=entry.provider_name,
                provider_type=entry.provider_type,
                effective_at=entry.effective_at,
                freshness_state=entry.freshness_state,
                is_fallback=entry.is_fallback,
                is_stale=self._staleness_resolver(
                    RateStalenessContext(
                        snapshot_id=snapshot_model.id,
                        captured_at=snapshot_model.captured_at,
                        currency_code=entry.currency_code,
                        provider_name=entry.provider_name,
                        provider_type=entry.provider_type,
                        effective_at=entry.effective_at,
                        freshness_state=entry.freshness_state,
                        is_fallback=entry.is_fallback,
                    )
                ),
            )
            for entry in entry_models
        )
        return RateSnapshot(
            snapshot_id=snapshot_model.id,
            captured_at=snapshot_model.captured_at,
            rates=rates,
        )
