"""FastAPI dependencies for configured application infrastructure."""

from collections.abc import Iterator, Sequence
from functools import lru_cache

from fastapi import Depends, Request
from sqlalchemy.orm import Session, sessionmaker

from app.application.services.snapshot_service import SnapshotService
from app.application.use_cases.get_latest_snapshot import GetLatestSnapshot
from app.application.use_cases.list_currencies import ListCurrencies
from app.core.config.settings import Settings, get_settings
from app.domain.interfaces.rate_provider import RateProvider
from app.domain.interfaces.unit_of_work import UnitOfWork
from app.infrastructure.database.session import create_session_factory
from app.infrastructure.database.unit_of_work import SqlAlchemyUnitOfWork
from app.infrastructure.providers.provider_factory import RateProviderFactory


@lru_cache(maxsize=8)
def _session_factory_for_url(database_url: str) -> sessionmaker[Session]:
    """Create and reuse a lazy engine/session factory for one configured URL."""
    return create_session_factory(database_url)


def get_app_settings(request: Request) -> Settings:
    """Return settings selected for this FastAPI application."""
    settings = getattr(request.app.state, "settings", None)
    return settings if isinstance(settings, Settings) else get_settings()


def _create_unit_of_work(settings: Settings) -> UnitOfWork:
    """Construct a fresh UnitOfWork without entering its context."""
    session_factory = _session_factory_for_url(settings.database_url)
    return SqlAlchemyUnitOfWork(session_factory=session_factory)


def get_unit_of_work(
    settings: Settings = Depends(get_app_settings),
) -> Iterator[UnitOfWork]:
    """Yield a request-scoped unit of work without committing on request exit."""
    with _create_unit_of_work(settings) as unit_of_work:
        yield unit_of_work


def get_list_currencies_use_case(
    settings: Settings = Depends(get_app_settings),
) -> ListCurrencies:
    """Construct the supported-currency use case with its own UnitOfWork."""
    return ListCurrencies(unit_of_work=_create_unit_of_work(settings))


def get_latest_snapshot_use_case(
    settings: Settings = Depends(get_app_settings),
) -> GetLatestSnapshot:
    """Construct the latest-snapshot use case with its own UnitOfWork."""
    return GetLatestSnapshot(unit_of_work=_create_unit_of_work(settings))


def get_rate_provider_factory(
    settings: Settings = Depends(get_app_settings),
) -> RateProviderFactory:
    """Build the provider factory from the application's configured settings."""
    return RateProviderFactory(settings=settings)


def get_rate_providers(
    factory: RateProviderFactory = Depends(get_rate_provider_factory),
) -> Sequence[RateProvider]:
    """Construct provider adapters without fetching rates."""
    return factory.create_all()


def get_snapshot_service(
    providers: Sequence[RateProvider] = Depends(get_rate_providers),
) -> SnapshotService:
    """Construct an in-memory snapshot assembler without fetching or persisting."""
    return SnapshotService(providers)
