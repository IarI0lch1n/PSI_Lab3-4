"""Sanitized HTTP exception handlers for application and infrastructure errors."""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.application.services.snapshot_service import SnapshotAssemblyError
from app.application.use_cases.convert_currency import (
    ConversionRateUnavailableError,
    ConversionSnapshotUnavailableError,
    InvalidConversionInputError,
)
from app.application.use_cases.get_latest_snapshot import (
    LatestSnapshotUnavailableError,
)
from app.infrastructure.providers.bnm_rate_provider import BnmRateProviderError
from app.infrastructure.providers.coingecko_rate_provider import (
    CoinGeckoRateProviderError,
)

_LOGGER = logging.getLogger("currencyhub.api")


async def handle_invalid_conversion_input_error(
    request: Request,
    exc: InvalidConversionInputError,
) -> JSONResponse:
    del request, exc
    return _error_response(
        422,
        "invalid_conversion_input",
        "Amount and currencies must be valid and supported.",
    )


async def handle_conversion_snapshot_unavailable_error(
    request: Request,
    exc: ConversionSnapshotUnavailableError,
) -> JSONResponse:
    del request, exc
    return _error_response(
        503,
        "conversion_unavailable",
        "Conversion is currently unavailable.",
    )


async def handle_conversion_rate_unavailable_error(
    request: Request,
    exc: ConversionRateUnavailableError,
) -> JSONResponse:
    del request
    return _error_response(
        422,
        "rate_unavailable",
        f"No usable rate is available for {exc.currency}.",
    )


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


async def handle_snapshot_assembly_error(
    request: Request,
    exc: SnapshotAssemblyError,
) -> JSONResponse:
    del request, exc
    return _error_response(
        503,
        "snapshot_unavailable",
        "A complete rate snapshot is currently unavailable.",
    )


async def handle_latest_snapshot_unavailable_error(
    request: Request,
    exc: LatestSnapshotUnavailableError,
) -> JSONResponse:
    del request, exc
    return _error_response(
        503,
        "snapshot_unavailable",
        "A complete rate snapshot is currently unavailable.",
    )


async def handle_provider_error(
    request: Request,
    exc: BnmRateProviderError | CoinGeckoRateProviderError,
) -> JSONResponse:
    del request, exc
    return _error_response(
        502,
        "provider_unavailable",
        "A rate provider is currently unavailable.",
    )


async def handle_database_error(
    request: Request,
    exc: SQLAlchemyError,
) -> JSONResponse:
    del request
    _LOGGER.error("Database operation failed (%s).", type(exc).__name__)
    return _error_response(
        503,
        "database_unavailable",
        "The database service is currently unavailable.",
    )


async def handle_unexpected_error(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    del request
    _LOGGER.error(
        "Unhandled application error.",
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    return _error_response(
        500,
        "internal_error",
        "An unexpected internal error occurred.",
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register common, sanitized error responses on a FastAPI application."""
    app.add_exception_handler(
        InvalidConversionInputError,
        handle_invalid_conversion_input_error,
    )
    app.add_exception_handler(
        ConversionSnapshotUnavailableError,
        handle_conversion_snapshot_unavailable_error,
    )
    app.add_exception_handler(
        ConversionRateUnavailableError,
        handle_conversion_rate_unavailable_error,
    )
    app.add_exception_handler(SnapshotAssemblyError, handle_snapshot_assembly_error)
    app.add_exception_handler(
        LatestSnapshotUnavailableError,
        handle_latest_snapshot_unavailable_error,
    )
    app.add_exception_handler(BnmRateProviderError, handle_provider_error)
    app.add_exception_handler(CoinGeckoRateProviderError, handle_provider_error)
    app.add_exception_handler(SQLAlchemyError, handle_database_error)
    app.add_exception_handler(Exception, handle_unexpected_error)
