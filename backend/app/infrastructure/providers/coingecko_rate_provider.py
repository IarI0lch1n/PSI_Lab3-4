"""CoinGecko adapter for normalized current and historical crypto rates."""

import json
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal, DecimalException
from types import MappingProxyType
from typing import Final

import httpx

from app.core.config.settings import Settings, get_settings
from app.domain.entities.currency import SUPPORTED_CRYPTO_CURRENCIES
from app.domain.enums.currency_type import CurrencyType
from app.domain.interfaces.rate_provider import ProviderRate, RateProvider


_PROVIDER_NAME: Final[str] = "CoinGecko"
_PRICE_ENDPOINT: Final[str] = "/simple/price"
_UNIX_EPOCH: Final[datetime] = datetime(1970, 1, 1, tzinfo=UTC)
_COINGECKO_IDS = MappingProxyType(
    {
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "SOL": "solana",
        "BNB": "binancecoin",
        "XRP": "ripple",
        "ADA": "cardano",
        "DOGE": "dogecoin",
        "USDT": "tether",
    }
)

if set(_COINGECKO_IDS) != set(SUPPORTED_CRYPTO_CURRENCIES):
    raise RuntimeError(
        "CoinGecko ID mapping must cover exactly the supported crypto currencies."
    )


class CoinGeckoRateProviderError(RuntimeError):
    """Raised when CoinGecko data cannot be fetched or parsed reliably."""


class CoinGeckoRateProvider(RateProvider):
    """Fetch and normalize CoinGecko prices without freshness policy."""

    def __init__(
        self,
        *,
        client: httpx.AsyncClient | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._client = client
        self._settings = settings or get_settings()
        self._base_url = self._settings.coingecko_base_url.rstrip("/")
        self._api_key = self._configured_api_key(
            self._settings.coingecko_api_key
        )

    async def fetch_latest_rates(self) -> Sequence[ProviderRate]:
        """Fetch all supported crypto prices quoted directly in MDL."""
        coin_ids = tuple(
            _COINGECKO_IDS[code] for code in SUPPORTED_CRYPTO_CURRENCIES
        )
        response = await self._request_prices(coin_ids)
        if not response.content.strip():
            raise CoinGeckoRateProviderError(
                "CoinGecko returned an empty JSON response."
            )
        return self._parse_response(response.text)

    async def fetch_historical_rates(
        self,
        currency_codes: Sequence[str],
        start_at: datetime,
        end_at: datetime,
    ) -> Sequence[ProviderRate]:
        """Fetch exact MDL price points in an inclusive UTC time window."""
        start_utc = self._aware_utc(start_at, "start_at")
        end_utc = self._aware_utc(end_at, "end_at")
        if start_utc > end_utc:
            raise CoinGeckoRateProviderError(
                "Historical start_at must not follow end_at."
            )

        requested_codes = {
            code.strip().upper()
            for code in currency_codes
            if code.strip().upper() in SUPPORTED_CRYPTO_CURRENCIES
        }
        if not requested_codes:
            return ()

        rates: list[ProviderRate] = []
        for currency_code in SUPPORTED_CRYPTO_CURRENCIES:
            if currency_code not in requested_codes:
                continue
            response = await self._request_market_chart(
                _COINGECKO_IDS[currency_code],
                start_utc,
                end_utc,
            )
            if not response.content.strip():
                raise CoinGeckoRateProviderError(
                    "CoinGecko returned an empty historical JSON response."
                )
            rates.extend(
                self._parse_market_chart_response(
                    response.text,
                    currency_code,
                    start_utc,
                    end_utc,
                )
            )

        currency_order = {
            code: index for index, code in enumerate(SUPPORTED_CRYPTO_CURRENCIES)
        }
        return tuple(
            sorted(
                rates,
                key=lambda rate: (
                    rate.effective_at,
                    currency_order[rate.currency],
                ),
            )
        )

    async def get_metadata(self) -> Mapping[str, str]:
        """Return non-secret provider identity and endpoint metadata."""
        return {
            "provider_name": _PROVIDER_NAME,
            "provider_type": CurrencyType.CRYPTO.value,
            "base_url": self._base_url,
        }

    async def _request_prices(
        self,
        coin_ids: Sequence[str],
    ) -> httpx.Response:
        url = f"{self._base_url}{_PRICE_ENDPOINT}"
        params = {
            "ids": ",".join(coin_ids),
            "vs_currencies": "mdl",
            "include_last_updated_at": "true",
        }
        return await self._request(url, params)

    async def _request_market_chart(
        self,
        coin_id: str,
        start_at: datetime,
        end_at: datetime,
    ) -> httpx.Response:
        url = f"{self._base_url}/coins/{coin_id}/market_chart/range"
        params = {
            "vs_currency": "mdl",
            "from": str(self._unix_seconds(start_at)),
            "to": str(self._unix_seconds(end_at, round_up=True)),
        }
        return await self._request(url, params)

    async def _request(
        self,
        url: str,
        params: Mapping[str, str],
    ) -> httpx.Response:
        headers = (
            {"x-cg-demo-api-key": self._api_key}
            if self._api_key is not None
            else {}
        )
        attempts = max(1, self._settings.coingecko_max_retries + 1)

        for attempt in range(attempts):
            try:
                if self._client is not None:
                    response = await self._client.get(
                        url,
                        params=params,
                        headers=headers,
                        timeout=self._settings.coingecko_timeout_seconds,
                    )
                else:
                    async with httpx.AsyncClient(
                        timeout=self._settings.coingecko_timeout_seconds
                    ) as client:
                        response = await client.get(
                            url,
                            params=params,
                            headers=headers,
                        )
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code
                retryable = status_code == 429 or status_code >= 500
                if not retryable or attempt + 1 == attempts:
                    raise CoinGeckoRateProviderError(
                        f"CoinGecko request failed with HTTP status {status_code}."
                    ) from None
            except httpx.RequestError:
                if attempt + 1 == attempts:
                    raise CoinGeckoRateProviderError(
                        f"CoinGecko request failed after {attempts} attempt(s)."
                    ) from None

        raise CoinGeckoRateProviderError(
            "CoinGecko request failed without a response."
        )

    @classmethod
    def _parse_market_chart_response(
        cls,
        body: str,
        currency_code: str,
        start_at: datetime,
        end_at: datetime,
    ) -> tuple[ProviderRate, ...]:
        try:
            data = json.loads(
                body,
                parse_float=Decimal,
                parse_int=Decimal,
                parse_constant=Decimal,
            )
        except (json.JSONDecodeError, DecimalException, ValueError):
            raise CoinGeckoRateProviderError(
                "CoinGecko returned malformed historical JSON."
            ) from None

        if not isinstance(data, dict) or not isinstance(
            data.get("prices"), list
        ):
            raise CoinGeckoRateProviderError(
                "CoinGecko historical JSON must contain a prices array."
            )

        rates_by_timestamp: dict[datetime, ProviderRate] = {}
        for point in data["prices"]:
            if not isinstance(point, list) or len(point) < 2:
                raise CoinGeckoRateProviderError(
                    "CoinGecko historical prices contain an invalid point."
                )
            timestamp, price = point[0], point[1]
            effective_at = cls._parse_millisecond_timestamp(timestamp)
            if (
                not isinstance(price, Decimal)
                or not price.is_finite()
                or price <= 0
            ):
                raise CoinGeckoRateProviderError(
                    "CoinGecko historical prices contain an invalid MDL price."
                )
            if not start_at <= effective_at <= end_at:
                continue
            if effective_at in rates_by_timestamp:
                raise CoinGeckoRateProviderError(
                    "CoinGecko historical prices contain a duplicate timestamp."
                )
            rates_by_timestamp[effective_at] = ProviderRate(
                currency=currency_code,
                normalized_rate_to_mdl=price,
                nominal_unit=1,
                provider_name=_PROVIDER_NAME,
                provider_type=CurrencyType.CRYPTO,
                effective_at=effective_at,
            )
        return tuple(rates_by_timestamp.values())

    @classmethod
    def _parse_response(cls, body: str) -> tuple[ProviderRate, ...]:
        try:
            data = json.loads(
                body,
                parse_float=Decimal,
                parse_int=Decimal,
                parse_constant=Decimal,
            )
        except (json.JSONDecodeError, DecimalException, ValueError):
            raise CoinGeckoRateProviderError(
                "CoinGecko returned malformed JSON."
            ) from None

        if not isinstance(data, dict):
            raise CoinGeckoRateProviderError(
                "CoinGecko JSON response must be an object."
            )

        rates: list[ProviderRate] = []
        for currency_code in SUPPORTED_CRYPTO_CURRENCIES:
            coin_id = _COINGECKO_IDS[currency_code]
            if coin_id not in data:
                raise CoinGeckoRateProviderError(
                    f"CoinGecko response is missing requested coin {coin_id}."
                )
            coin_data = data[coin_id]
            if not isinstance(coin_data, dict):
                raise CoinGeckoRateProviderError(
                    f"CoinGecko response for {coin_id} must be an object."
                )
            if "mdl" not in coin_data:
                raise CoinGeckoRateProviderError(
                    f"CoinGecko response for {coin_id} is missing mdl."
                )

            price = coin_data["mdl"]
            if not isinstance(price, Decimal):
                raise CoinGeckoRateProviderError(
                    f"CoinGecko response for {coin_id} has an invalid mdl price."
                )
            if not price.is_finite() or price <= 0:
                raise CoinGeckoRateProviderError(
                    f"CoinGecko response for {coin_id} has a non-positive or non-finite mdl price."
                )
            if "last_updated_at" not in coin_data:
                raise CoinGeckoRateProviderError(
                    f"CoinGecko response for {coin_id} is missing last_updated_at."
                )
            effective_at = cls._parse_effective_at(
                coin_data["last_updated_at"],
                coin_id,
            )

            rates.append(
                ProviderRate(
                    currency=currency_code,
                    normalized_rate_to_mdl=price,
                    nominal_unit=1,
                    provider_name=_PROVIDER_NAME,
                    provider_type=CurrencyType.CRYPTO,
                    effective_at=effective_at,
                )
            )

        return tuple(rates)

    @staticmethod
    def _parse_effective_at(value: object, coin_id: str) -> datetime:
        if (
            isinstance(value, bool)
            or not isinstance(value, Decimal)
            or not value.is_finite()
            or value <= 0
            or value != value.to_integral_value()
        ):
            raise CoinGeckoRateProviderError(
                f"CoinGecko response for {coin_id} has an invalid last_updated_at."
            )

        try:
            return _UNIX_EPOCH + timedelta(seconds=int(value))
        except (OverflowError, ValueError):
            raise CoinGeckoRateProviderError(
                f"CoinGecko response for {coin_id} has an out-of-range last_updated_at."
            ) from None

    @staticmethod
    def _parse_millisecond_timestamp(value: object) -> datetime:
        if (
            isinstance(value, bool)
            or not isinstance(value, Decimal)
            or not value.is_finite()
            or value <= 0
            or value != value.to_integral_value()
        ):
            raise CoinGeckoRateProviderError(
                "CoinGecko historical prices contain an invalid timestamp."
            )
        try:
            return _UNIX_EPOCH + timedelta(milliseconds=int(value))
        except (OverflowError, ValueError):
            raise CoinGeckoRateProviderError(
                "CoinGecko historical prices contain an out-of-range timestamp."
            ) from None

    @staticmethod
    def _aware_utc(value: datetime, field_name: str) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise CoinGeckoRateProviderError(
                f"Historical {field_name} must be timezone-aware."
            )
        return value.astimezone(UTC)

    @staticmethod
    def _unix_seconds(value: datetime, *, round_up: bool = False) -> int:
        elapsed = value - _UNIX_EPOCH
        seconds = elapsed.days * 86_400 + elapsed.seconds
        if round_up and elapsed.microseconds:
            seconds += 1
        return seconds

    @staticmethod
    def _configured_api_key(value: str) -> str | None:
        normalized = value.strip()
        placeholder_markers = ("placeholder", "your_", "changeme", "replace_me")
        if not normalized or any(
            marker in normalized.lower() for marker in placeholder_markers
        ):
            return None
        return normalized
