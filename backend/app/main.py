"""FastAPI application entry point for CurrencyHub."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.dependencies import _create_unit_of_work
from app.api.exception_handlers import register_exception_handlers
from app.api.routers.conversion import router as conversion_router
from app.api.routers.analytics import router as analytics_router
from app.api.routers.health import router as health_router
from app.api.routers.rates import router as rates_router
from app.application.services.rate_refresh_coordinator import RateRefreshCoordinator
from app.application.use_cases.refresh_rates import RefreshRates
from app.core.config.settings import Settings, get_settings
from app.core.logging.logger import configure_logging
from app.infrastructure.providers.provider_factory import RateProviderFactory


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Start and stop the app-scoped current-rate refresh lifecycle."""
    coordinator = getattr(application.state, "rate_refresh_coordinator", None)
    if coordinator is None:
        settings = getattr(application.state, "settings", None)
        if settings is None:
            settings = get_settings()
            application.state.settings = settings

        if settings.rate_auto_refresh_enabled:
            provider_factory = RateProviderFactory(settings=settings)
            providers = provider_factory.create_all()
            use_case = RefreshRates(
                providers,
                unit_of_work=_create_unit_of_work(settings),
            )
            coordinator = RateRefreshCoordinator(
                settings,
                refresh_callable=use_case.execute,
            )
        else:
            coordinator = RateRefreshCoordinator(settings)
        application.state.rate_refresh_coordinator = coordinator

    await coordinator.start()
    try:
        yield
    finally:
        await coordinator.stop()


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create the API application without connecting to external services."""
    app_settings = settings or get_settings()
    configure_logging(app_settings)

    application = FastAPI(
        title="CurrencyHub API",
        description="Currency conversion and exchange-rate analytics platform",
        version="0.1.0",
        lifespan=lifespan,
    )
    application.state.settings = app_settings
    application.include_router(conversion_router, prefix="/api/v1")
    application.include_router(analytics_router, prefix="/api/v1")
    application.include_router(rates_router, prefix="/api/v1")
    application.include_router(health_router, prefix="/api/v1")
    application.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Accept", "Content-Type"],
    )
    register_exception_handlers(application)

    @application.get("/")
    def read_root() -> dict[str, str]:
        """Root entry point returning welcome message."""
        return {"message": "Welcome to CurrencyHub API"}

    return application


app = create_app()
