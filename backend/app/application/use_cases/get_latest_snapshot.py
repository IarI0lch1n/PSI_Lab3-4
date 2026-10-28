"""Use case for retrieving the latest usable rate snapshot."""

from app.domain.entities.rate_snapshot import RateSnapshot
from app.domain.interfaces.unit_of_work import UnitOfWork


class LatestSnapshotUnavailableError(Exception):
    """Raised when no usable rate snapshot is available."""

    def __init__(self) -> None:
        super().__init__("No usable rate snapshot is available.")


class GetLatestSnapshot:
    """Return the latest complete usable snapshot without modifying it."""

    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    def execute(self) -> RateSnapshot:
        """Retrieve the repository-selected snapshot without committing."""
        with self._unit_of_work as uow:
            snapshot = uow.rate_repository.get_latest_usable_snapshot()
            if snapshot is None:
                raise LatestSnapshotUnavailableError
            return snapshot
