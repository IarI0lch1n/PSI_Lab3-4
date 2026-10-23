"""Repository contract for complete normalized rate snapshots."""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from app.domain.entities.rate_snapshot import RateSnapshot


class RateRepository(ABC):
    """Access and persist normalized rate snapshots."""

    @abstractmethod
    def get_latest_usable_snapshot(self) -> RateSnapshot | None:
        """Return the latest complete usable snapshot, if one exists."""

    @abstractmethod
    def get_snapshot_by_id(self, snapshot_id: UUID) -> RateSnapshot | None:
        """Return a snapshot by identifier, or ``None`` when it does not exist."""

    @abstractmethod
    def save_complete_snapshot(self, snapshot: RateSnapshot) -> None:
        """Persist a complete snapshot and activate it within the current transaction."""

    @abstractmethod
    def get_historical_snapshots(
        self,
        start_at: datetime,
        end_at: datetime,
        currency_codes: Sequence[str] | None = None,
    ) -> Sequence[RateSnapshot]:
        """Return normalized snapshots in a time window, optionally filtered by currency."""
