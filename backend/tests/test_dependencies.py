"""Tests for lazy FastAPI infrastructure dependency wiring."""

from typing import cast

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

import app.api.dependencies as dependencies
from app.application.services.snapshot_service import SnapshotService
from app.core.config.settings import Settings
from app.domain.interfaces.rate_provider import RateProvider
from app.domain.interfaces.unit_of_work import UnitOfWork
from app.infrastructure.providers.bnm_rate_provider import BnmRateProvider
from app.infrastructure.providers.coingecko_rate_provider import (
    CoinGeckoRateProvider,
)
from app.infrastructure.providers.provider_factory import RateProviderFactory
from app.main import create_app


def test_settings_and_factory_dependencies_use_application_configuration() -> None:
    settings = Settings(
        database_url="sqlite:///test.db",
        bnm_base_url="https://bnm.example",
        coingecko_base_url="https://coingecko.example/api/v3",
    )
    application = create_app(settings)

    @application.get("/test-config")
    def read_config(
        resolved_settings: Settings = Depends(dependencies.get_app_settings),
        factory: RateProviderFactory = Depends(
            dependencies.get_rate_provider_factory
        ),
    ) -> dict[str, str]:
        return {
            "database_url": resolved_settings.database_url,
            "bnm_url": factory.create_for("fiat")._base_url,
        }

    with TestClient(application) as client:
        response = client.get("/test-config")

    assert response.json() == {
        "database_url": "sqlite:///test.db",
        "bnm_url": "https://bnm.example",
    }


def test_provider_and_snapshot_dependencies_construct_without_fetching(
    monkeypatch,
) -> None:
    fetches: list[str] = []

    async def record_bnm_fetch(self):
        del self
        fetches.append("bnm")
        return ()

    async def record_coingecko_fetch(self):
        del self
        fetches.append("coingecko")
        return ()

    monkeypatch.setattr(BnmRateProvider, "fetch_latest_rates", record_bnm_fetch)
    monkeypatch.setattr(
        CoinGeckoRateProvider,
        "fetch_latest_rates",
        record_coingecko_fetch,
    )
    application = create_app(Settings())

    @application.get("/test-providers")
    def read_providers(
        providers: tuple[RateProvider, ...] = Depends(dependencies.get_rate_providers),
        service: SnapshotService = Depends(dependencies.get_snapshot_service),
    ) -> dict[str, object]:
        return {
            "types": [type(provider).__name__ for provider in providers],
            "same_providers": service._providers == providers,
        }

    with TestClient(application) as client:
        response = client.get("/test-providers")

    assert response.status_code == 200
    assert response.json() == {
        "types": ["BnmRateProvider", "CoinGeckoRateProvider"],
        "same_providers": True,
    }
    assert fetches == []


def test_unit_of_work_dependency_is_lazy_and_rolls_back_closes_on_exit(
    monkeypatch,
) -> None:
    session_events: list[str] = []
    factory_calls: list[str] = []

    class FakeSession:
        def rollback(self) -> None:
            session_events.append("rollback")

        def close(self) -> None:
            session_events.append("close")

    session = FakeSession()

    def session_factory_for_url(url: str):
        factory_calls.append(url)
        return lambda: session

    monkeypatch.setattr(
        dependencies,
        "_session_factory_for_url",
        session_factory_for_url,
    )
    application = create_app(Settings(database_url="mssql+pyodbc://test"))

    @application.get("/test-uow")
    def read_uow(uow: UnitOfWork = Depends(dependencies.get_unit_of_work)):
        assert uow.currency_repository is not None
        assert uow.rate_repository is not None
        return {"ready": True}

    assert factory_calls == []
    assert session_events == []

    with TestClient(application) as client:
        response = client.get("/test-uow")

    assert response.status_code == 200
    assert factory_calls == ["mssql+pyodbc://test"]
    assert session_events == ["rollback", "close"]


def test_unit_of_work_dependency_can_be_overridden() -> None:
    application = create_app()

    class FakeUnitOfWork:
        currency_repository = object()
        rate_repository = object()

    fake_uow = FakeUnitOfWork()
    application.dependency_overrides[dependencies.get_unit_of_work] = (
        lambda: cast(UnitOfWork, fake_uow)
    )

    @application.get("/test-overridden-uow")
    def read_uow(uow: UnitOfWork = Depends(dependencies.get_unit_of_work)):
        return {"is_override": uow is fake_uow}

    with TestClient(application) as client:
        response = client.get("/test-overridden-uow")

    assert response.json() == {"is_override": True}


def test_use_case_dependencies_construct_unentered_unit_of_work(monkeypatch) -> None:
    events: list[str] = []
    created: list[object] = []

    class FakeUnitOfWork:
        class CurrencyRepository:
            def get_supported_currencies(self):
                return ()

        class RateRepository:
            def get_latest_usable_snapshot(self):
                return None

        currency_repository = CurrencyRepository()
        rate_repository = RateRepository()

        def __enter__(self):
            events.append("enter")
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            events.append("exit")

    def create_unit_of_work(settings: Settings) -> UnitOfWork:
        del settings
        unit_of_work = FakeUnitOfWork()
        created.append(unit_of_work)
        return cast(UnitOfWork, unit_of_work)

    monkeypatch.setattr(dependencies, "_create_unit_of_work", create_unit_of_work)

    list_use_case = dependencies.get_list_currencies_use_case(Settings())
    latest_use_case = dependencies.get_latest_snapshot_use_case(Settings())

    assert len(created) == 2
    assert created[0] is not created[1]
    assert events == []
    assert list_use_case.execute() == ()
    assert events == ["enter", "exit"]
    assert latest_use_case._unit_of_work is created[1]
    assert events == ["enter", "exit"]
