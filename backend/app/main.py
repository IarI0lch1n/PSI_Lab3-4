"""FastAPI application entry point for CurrencyHub."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.exception_handlers import register_exception_handlers
from app.api.routers.rates import router as rates_router
from app.core.config.settings import Settings, get_settings
from app.core.logging.logger import configure_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create the API application without connecting to external services."""
    app_settings = settings or get_settings()
    configure_logging(app_settings)

    application = FastAPI(
        title="CurrencyHub API",
        description="Currency conversion and exchange-rate analytics platform",
        version="0.1.0",
    )
    application.state.settings = app_settings
    application.include_router(rates_router, prefix="/api/v1")
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
