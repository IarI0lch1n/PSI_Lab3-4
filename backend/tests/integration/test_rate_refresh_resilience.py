"""Integration tests for atomic refresh replacement and outage preservation."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.api.dependencies import get_refresh_rates_use_case
from app.application.use_cases.refresh_rates import RefreshRates
from app.core.config.settings import Settings
from app.domain.entities.currency import (
    SUPPORTED_CRYPTO_CURRENCIES,
    SUPPORTED_FIAT_CURRENCIES,
)
from app.domain.entities.rate_entry import RateEntry
from app.domain.entities.rate_snapshot import RateSnapshot
from app.domain.enums.currency_type import CurrencyType
from app.domain.enums.freshness_state import FreshnessState
from app.main import create_app
from tests.fixtures.fake_rate_providers import (
    FakeBnmRateProvider,
    FakeCoinGeckoRateProvider,
    make_complete_crypto_rates,
    make_complete_fiat_rates,
)


_NOW = datetime(2026, 11, 2, 10, 0, tzinfo=UTC)
_NEW_ID = UUID("00000000-0000-0000-0000-000000000154")


def _complete_snapshot() -> RateSnapshot:
    snapshot_id = uuid4()
    captured_at = _NOW - timedelta(hours=1)
    entries = []
    for index, code in enumerate(SUPPORTED_FIAT_CURRENCIES, start=1):
        entries.append(
            RateEntry(
                snapshot_id=snapshot_id,
                currency=code,
                normalized_rate_to_mdl=(
                    Decimal("1") if code == "MDL" else Decimal(index)
                ),
                provider_name=(
                    "CurrencyHub Reference" if code == "MDL" else "Stored BNM"
                ),
                provider_type=CurrencyType.FIAT,
                effective_at=captured_at,
                freshness_state=FreshnessState.LIVE,
            )
        )
    for index, code in enumerate(SUPPORTED_CRYPTO_CURRENCIES, start=1):
        entries.append(
            RateEntry(
                snapshot_id=snapshot_id,
                currency=code,
                normalized_rate_to_mdl=Decimal(index),
                provider_name="Stored CoinGecko",
                provider_type=CurrencyType.CRYPTO,
                effective_at=captured_at - timedelta(minutes=1),
                freshness_state=FreshnessState.LIVE,
            )
        )
    return RateSnapshot(snapshot_id, captured_at, entries)


class _Repository:
    def __init__(self, previous: RateSnapshot | None) -> None:
        self.active = previous
        self.saved: list[RateSnapshot] = []

    def get_latest_usable_snapshot(self) -> RateSnapshot | None:
        return self.active

    def save_complete_snapshot(self, snapshot: RateSnapshot) -> None:
        self.saved.append(snapshot)
        self.active = snapshot


class _UnitOfWork:
    def __init__(self, previous: RateSnapshot | None) -> None:
        self.rate_repository = _Repository(previous)
        self.commit_count = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        del exc_type, exc_value, traceback

    def commit(self) -> None:
        self.commit_count += 1


def _client(
    unit_of_work: _UnitOfWork,
    *,
    crypto_failure: bool = False,
    invalid_fiat_response: bool = False,
) -> TestClient:
    fiat_rates = make_complete_fiat_rates(effective_at=_NOW)
    if invalid_fiat_response:
        fiat_rates = (*fiat_rates, fiat_rates[0])

    providers = (
        FakeBnmRateProvider(latest_rates=fiat_rates),
        FakeCoinGeckoRateProvider(
            latest_rates=(
                ()
                if crypto_failure
                else make_complete_crypto_rates(effective_at=_NOW)
            ),
            latest_error=(RuntimeError("offline") if crypto_failure else None),
        ),
    )
    use_case = RefreshRates(
        providers,
        unit_of_work=unit_of_work,
        clock=lambda: _NOW,
        snapshot_id_factory=lambda: _NEW_ID,
    )
    application = create_app(Settings())
    application.dependency_overrides[get_refresh_rates_use_case] = lambda: use_case
    return TestClient(application, raise_server_exceptions=False)


def test_complete_refresh_atomically_replaces_snapshot_and_reports_counts() -> None:
    unit_of_work = _UnitOfWork(_complete_snapshot())

    with _client(unit_of_work) as client:
        response = client.post("/api/v1/rates/refresh")

    assert response.status_code == 200
    payload = response.json()
    assert payload["snapshot_id"] == str(_NEW_ID)
    assert payload["updated"] is True
    assert payload["rate_count"] == 18
    assert payload["freshness_summary"] == {
        "rate_entry_freshness_counts": {
            "live": 18,
            "fallback": 0,
            "cached": 0,
        },
        "stale_entry_count": 0,
        "fallback_entry_count": 0,
    }
    assert len(unit_of_work.rate_repository.saved) == 1
    assert unit_of_work.commit_count == 1
    assert unit_of_work.rate_repository.active is unit_of_work.rate_repository.saved[0]


def test_refresh_commits_complete_candidate_with_reused_cached_crypto_rates() -> None:
    previous = _complete_snapshot()
    previous_btc = previous.get_rate("BTC")
    assert previous_btc is not None
    unit_of_work = _UnitOfWork(previous)

    with _client(unit_of_work, crypto_failure=True) as client:
        response = client.post("/api/v1/rates/refresh")

    assert response.status_code == 200
    payload = response.json()
    assert payload["snapshot_id"] == str(_NEW_ID)
    assert payload["updated"] is True
    assert payload["rate_count"] == 18
    assert payload["freshness_summary"] == {
        "rate_entry_freshness_counts": {
            "live": 10,
            "fallback": 0,
            "cached": 8,
        },
        "stale_entry_count": 8,
        "fallback_entry_count": 0,
    }

    candidate = unit_of_work.rate_repository.active
    assert candidate is not previous
    assert len(candidate.rates) == 18
    assert candidate.currencies == previous.currencies

    usd = candidate.get_rate("USD")
    assert usd is not None
    assert usd.provider_name == "Fake BNM"
    assert usd.effective_at == _NOW
    assert usd.freshness_state is FreshnessState.LIVE

    btc = candidate.get_rate("BTC")
    assert btc is not None
    assert btc.provider_name == previous_btc.provider_name
    assert btc.effective_at == previous_btc.effective_at
    assert btc.freshness_state is FreshnessState.CACHED
    assert not btc.is_fallback
    assert btc.is_stale

    assert unit_of_work.rate_repository.saved == [candidate]
    assert unit_of_work.commit_count == 1


def test_invalid_candidate_preserves_previous_complete_snapshot_without_partial_save() -> None:
    previous = _complete_snapshot()
    unit_of_work = _UnitOfWork(previous)

    with _client(unit_of_work, invalid_fiat_response=True) as client:
        response = client.post("/api/v1/rates/refresh")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "snapshot_unavailable"
    assert unit_of_work.rate_repository.active is previous
    assert unit_of_work.rate_repository.saved == []
    assert unit_of_work.commit_count == 0


def test_failed_refresh_without_usable_snapshot_returns_unavailable() -> None:
    unit_of_work = _UnitOfWork(None)

    with _client(unit_of_work, crypto_failure=True) as client:
        response = client.post("/api/v1/rates/refresh")

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "snapshot_unavailable",
            "message": "A complete rate snapshot is currently unavailable.",
        }
    }
    assert unit_of_work.rate_repository.saved == []
    assert unit_of_work.commit_count == 0
