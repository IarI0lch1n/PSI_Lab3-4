"""Shared coordinator for startup, periodic, and manual rate refreshes."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from app.application.use_cases.refresh_rates import RefreshResult
from app.core.config.settings import Settings
from app.core.logging.logger import get_logger


class RateRefreshCoordinator:
    """Serialize refresh work while allowing the app lifecycle to manage it."""

    def __init__(
        self,
        settings: Settings,
        *,
        refresh_callable: Callable[[], Awaitable[RefreshResult]] | None = None,
    ) -> None:
        self.settings = settings
        self._refresh_callable = refresh_callable
        self._lock = asyncio.Lock()
        self._background_task: asyncio.Task[Any] | None = None
        self._logger = get_logger("currencyhub.rate_refresh")

    @property
    def enabled(self) -> bool:
        return self.settings.rate_auto_refresh_enabled

    async def start(self) -> None:
        """Schedule the periodic refresh loop if auto-refresh is enabled."""
        if not self.enabled:
            self._logger.info(
                "Background current-rate refresh is disabled.",
                extra={"enabled": False},
            )
            return

        if self._background_task is not None and not self._background_task.done():
            return

        self._background_task = asyncio.create_task(self._run_background_loop())

    async def stop(self) -> None:
        """Cancel the background task and await it cleanly."""
        if self._background_task is None:
            return

        self._background_task.cancel()
        try:
            await self._background_task
        except asyncio.CancelledError:
            self._logger.info("Background current-rate refresh task cancelled.")
        finally:
            self._background_task = None

    async def refresh(self, *, refresh_callable: Callable[[], Awaitable[RefreshResult]] | None = None) -> RefreshResult:
        """Run one refresh while serializing access across lifecycle and manual calls."""
        candidate_callable = refresh_callable or self._refresh_callable
        if candidate_callable is None:
            raise RuntimeError("RateRefreshCoordinator requires a refresh callable.")

        async with self._lock:
            return await candidate_callable()

    async def _run_background_loop(self) -> None:
        try:
            await self._run_refresh_once("startup")
            while True:
                await asyncio.sleep(self.settings.rate_auto_refresh_interval_seconds)
                await self._run_refresh_once("periodic")
        except asyncio.CancelledError:
            self._logger.info("Background current-rate refresh loop cancelled.")
            raise

    async def _run_refresh_once(self, source: str) -> None:
        try:
            result = await self.refresh()
            self._logger.info(
                "Current-rate refresh completed.",
                extra={
                    "source": source,
                    "updated": bool(getattr(result, "updated", False)),
                    "snapshot_id": str(getattr(result.snapshot, "snapshot_id", "")),
                },
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            self._logger.exception(
                "Current-rate refresh failed while running %s; keeping the previous usable snapshot.",
                source,
            )
