"""Focused tests for provider and backend health reporting."""

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_latest_snapshot_use_case,
    get_rate_providers,
)
from app.application.use_cases.get_latest_snapshot import (
    LatestSnapshotUnavailableError,
)
from app.core.config.settings import Settings
from app.domain.entities.rate_entry import RateEntry
from app.domain.entities.rate_snapshot import RateSnapshot
from app.domain.enums.currency_type import CurrencyType
from app.domain.enums.freshness_state import FreshnessState
from app.domain.interfaces.rate_provider import ProviderRate, RateProvider
from app.main import create_app


_SNAPSHOT_ID = UUID("00000000-0000-0000-0000-000000000401")
_CAPTURED_AT = datetime(2026, 10, 28, 12, 0, tzinfo=UTC)
_EFFECTIVE_AT = datetime(2026, 10, 28, 10, 0, tzinfo=UTC)


class FakeRateProvider(RateProvider):
    def __init__(
        self,
        name: str,
        *,
        fetch_error: Exception | None = None,
        metadata_error: Exception | None = None,
    ) -> None:
        self.name = name
        self.fetch_error = fetch_error
        self.metadata_error = metadata_error
        self.metadata_calls = 0
        self.latest_calls = 0

    async def get_metadata(self) -> Mapping[str, str]:
        self.metadata_calls += 1
        if self.metadata_error is not None:
            raise self.metadata_error
        return {"provider_name": self.name}

    async def fetch_latest_rates(self) -> Sequence[ProviderRate]:
        self.latest_calls += 1
        if self.fetch_error is not None:
            raise self.fetch_error
        return ()

    async def fetch_historical_rates(
        self,
        currency_codes: Sequence[str],
        start_at: datetime,
        end_at: datetime,
    ) -> Sequence[ProviderRate]:
        raise NotImplementedError


class FakeGetLatestSnapshot:
    def __init__(
        self,
        snapshot: RateSnapshot | None = None,
        *,
        unavailable: bool = False,
    ) -> None:
        self.snapshot = snapshot
        self.unavailable = unavailable

    def execute(self) -> RateSnapshot:
        if self.unavailable:
            raise LatestSnapshotUnavailableError
        assert self.snapshot is not None
        return self.snapshot


def _snapshot() -> RateSnapshot:
    return RateSnapshot(
        _SNAPSHOT_ID,
        _CAPTURED_AT,
        (
            RateEntry(
                snapshot_id=_SNAPSHOT_ID,
                entry_id=UUID("00000000-0000-0000-0000-000000000411"),
                currency="RON",
                normalized_rate_to_mdl=Decimal("3.9123"),
                provider_name="BNM",
                provider_type=CurrencyType.FIAT,
                effective_at=_EFFECTIVE_AT,
                freshness_state=FreshnessState.FALLBACK,
                is_fallback=True,
                is_stale=False,
            ),
            RateEntry(
                snapshot_id=_SNAPSHOT_ID,
                entry_id=UUID("00000000-0000-0000-0000-000000000412"),
                currency="BTC",
                normalized_rate_to_mdl=Decimal("542240.10"),
                provider_name="CoinGecko",
                provider_type=CurrencyType.CRYPTO,
                effective_at=_EFFECTIVE_AT,
                freshness_state=FreshnessState.CACHED,
                is_fallback=False,
                is_stale=True,
            ),
        ),
    )


def _client(
    providers: tuple[RateProvider, ...],
    snapshot_use_case: FakeGetLatestSnapshot,
) -> TestClient:
    application = create_app(Settings())
    application.dependency_overrides[get_rate_providers] = lambda: providers
    application.dependency_overrides[get_latest_snapshot_use_case] = (
        lambda: snapshot_use_case
    )
    return TestClient(application, raise_server_exceptions=False)


def test_health_reports_healthy_providers_and_last_snapshot() -> None:
    providers = (FakeRateProvider("BNM"), FakeRateProvider("CoinGecko"))
    snapshot_use_case = FakeGetLatestSnapshot(_snapshot())

    application = _client(providers, snapshot_use_case)
    assert [provider.latest_calls for provider in providers] == [0, 0]
    with application as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "backend": "healthy",
        "providers": {"BNM": "healthy", "CoinGecko": "healthy"},
        "last_successful_snapshot": "2026-10-28T12:00:00Z",
    }
    assert [provider.metadata_calls for provider in providers] == [1, 1]
    assert [provider.latest_calls for provider in providers] == [1, 1]


def test_health_degrades_only_the_provider_that_fails_and_hides_error() -> None:
    secret_error = "secret upstream details"
    providers = (
        FakeRateProvider("BNM"),
        FakeRateProvider("CoinGecko", fetch_error=RuntimeError(secret_error)),
    )
    with _client(providers, FakeGetLatestSnapshot(_snapshot())) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["backend"] == "healthy"
    assert response.json()["providers"] == {
        "BNM": "healthy",
        "CoinGecko": "unhealthy",
    }
    assert secret_error not in response.text


def test_health_without_snapshot_remains_healthy_when_providers_succeed() -> None:
    providers = (FakeRateProvider("BNM"), FakeRateProvider("CoinGecko"))
    with _client(
        providers,
        FakeGetLatestSnapshot(unavailable=True),
    ) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "backend": "healthy",
        "providers": {"BNM": "healthy", "CoinGecko": "healthy"},
        "last_successful_snapshot": None,
    }


def test_health_provider_status_is_independent_of_rate_freshness() -> None:
    providers = (FakeRateProvider("BNM"), FakeRateProvider("CoinGecko"))
    snapshot = _snapshot()
    assert snapshot.rates[0].freshness_state is FreshnessState.FALLBACK
    assert snapshot.rates[0].is_fallback is True
    assert snapshot.rates[0].is_stale is False
    assert snapshot.rates[1].freshness_state is FreshnessState.CACHED
    assert snapshot.rates[1].is_fallback is False
    assert snapshot.rates[1].is_stale is True

    with _client(providers, FakeGetLatestSnapshot(snapshot)) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["providers"] == {
        "BNM": "healthy",
        "CoinGecko": "healthy",
    }
    assert "freshness_state" not in response.json()
    assert "is_stale" not in response.json()
    assert "is_fallback" not in response.json()


def test_health_reports_unhealthy_if_metadata_probe_fails_without_leaking_error() -> None:
    secret_error = "credentials in upstream failure"
    providers = (
        FakeRateProvider("BNM", metadata_error=RuntimeError(secret_error)),
        FakeRateProvider("CoinGecko"),
    )
    with _client(providers, FakeGetLatestSnapshot(_snapshot())) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert list(response.json()["providers"].values()) == ["unhealthy", "healthy"]
    assert secret_error not in response.text
